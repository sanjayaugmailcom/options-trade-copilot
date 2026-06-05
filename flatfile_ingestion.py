"""
Massive flat-file ingestion — options minute aggregates via S3.

Downloads daily CSV.gz files, parses OCC symbols with vectorised pandas,
filters to configured tickers, and bulk-inserts into options_quotes.

Usage:
    python flatfile_ingestion.py                              # yesterday
    python flatfile_ingestion.py --days 30                   # last 30 trading days
    python flatfile_ingestion.py --from-date 2026-01-01      # from date to yesterday
    python flatfile_ingestion.py --from-date 2026-01-01 --to-date 2026-06-04
"""
import os
import io
import gzip
import logging
import argparse
from datetime import date, datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

import boto3
import pandas as pd
from botocore.config import Config
from dotenv import load_dotenv

from db_client import TimescaleDBClient

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ── S3 config ─────────────────────────────────────────────────────────────────

S3_ENDPOINT     = "https://files.massive.com"
S3_BUCKET       = "flatfiles"
S3_KEY_TEMPLATE = "us_options_opra/minute_aggs_v1/{year}/{month:02d}/{date_str}.csv.gz"

# ── S3 helpers ────────────────────────────────────────────────────────────────

def _s3_client():
    return boto3.Session(
        aws_access_key_id=os.getenv("MASSIVE_S3_ACCESS_KEY"),
        aws_secret_access_key=os.getenv("MASSIVE_S3_SECRET_KEY"),
    ).client(
        "s3",
        endpoint_url=S3_ENDPOINT,
        config=Config(signature_version="s3v4"),
    )


def _download_df(target_date: date) -> pd.DataFrame | None:
    """Download the flat file for target_date and return as a DataFrame."""
    key = S3_KEY_TEMPLATE.format(
        year=target_date.year,
        month=target_date.month,
        date_str=target_date.isoformat(),
    )
    try:
        buf = io.BytesIO()
        _s3_client().download_fileobj(S3_BUCKET, key, buf)
        buf.seek(0)
        with gzip.open(buf, "rt") as f:
            df = pd.read_csv(f)
        logger.info(f"  {target_date}: {len(df):,} rows downloaded")
        return df
    except Exception as e:
        # 404 = market holiday or weekend — expected, not an error
        err_code = getattr(getattr(e, "response", None), "status_code", None) or \
                   (e.response["Error"]["Code"] if hasattr(e, "response") and isinstance(e.response, dict) else None)
        if "404" in str(e) or err_code in ("404", "NoSuchKey"):
            logger.debug(f"  {target_date}: no file (market holiday or weekend)")
        else:
            logger.warning(f"  {target_date}: download failed — {e}")
        return None


# ── Transform ─────────────────────────────────────────────────────────────────

def _transform(df: pd.DataFrame, ticker_set: set[str], today: date, file_date: date = None) -> pd.DataFrame:
    """
    Vectorised parse of OCC symbols, filter to our tickers and future expiries,
    and reshape into the options_quotes column layout.

    OCC format: O:NVDA260605C00220000
      underlying = NVDA
      yy/mm/dd   = 26/06/05  → 2026-06-05
      opt_type   = C
      strike_raw = 00220000  → 220.000
    """
    # Extract OCC components in one vectorised pass
    occ = df["ticker"].str.extract(
        r"^O:([A-Z]{1,6})(\d{2})(\d{2})(\d{2})([CP])(\d{8})$",
        expand=True,
    )
    occ.columns = ["underlying", "yy", "mm", "dd", "opt_type", "strike_raw"]

    # Drop rows that didn't match (indices/ETF fund tickers etc.)
    valid = occ["underlying"].notna()
    df = df[valid].copy()
    occ = occ[valid]

    # Filter to our tickers
    in_universe = occ["underlying"].isin(ticker_set)
    df = df[in_universe].copy()
    occ = occ[in_universe]

    if df.empty:
        return df

    # Derive expiration_date
    expiry_str = "20" + occ["yy"] + occ["mm"] + occ["dd"]
    expiry_dates = pd.to_datetime(expiry_str, format="%Y%m%d").dt.date

    # Keep only contracts expiring today or in the future
    future = expiry_dates >= today
    df = df[future.values].copy()
    occ = occ[future.values]
    expiry_dates = expiry_dates[future.values]

    if df.empty:
        return df

    # Build output frame
    ts_utc = pd.to_datetime(df["window_start"].values, unit="ns", utc=True)

    out = pd.DataFrame({
        "time":               ts_utc,
        "ticker":             occ["underlying"].values,
        "option_symbol":      df["ticker"].values,
        "strike":             occ["strike_raw"].astype(float).values / 1000.0,
        "expiration_date":    expiry_dates.values,
        "option_type":        occ["opt_type"].values,
        "bid":                None,
        "ask":                None,
        "last":               df["close"].values,
        "volume":             df["volume"].values,
        "open_interest":      None,
        "delta":              None,
        "gamma":              None,
        "theta":              None,
        "vega":               None,
        "rho":                None,
        "iv":                 None,
        "source":             "flatfile",
        "polygon_request_id": file_date.isoformat() if file_date else None,
    })

    return out


# ── Per-date ingestion ────────────────────────────────────────────────────────

def ingest_date(target_date: date, ticker_set: set[str], db: TimescaleDBClient) -> int:
    """Download, transform, and insert one day of flat-file data. Returns rows inserted."""
    df_raw = _download_df(target_date)
    if df_raw is None or df_raw.empty:
        return 0

    today = date.today()
    df = _transform(df_raw, ticker_set, today, file_date=target_date)
    if df.empty:
        logger.warning(f"  {target_date}: no matching rows after filter")
        return 0

    logger.info(f"  {target_date}: {len(df):,} rows after filter — inserting…")
    records = df.to_dict("records")
    inserted = db.insert_quotes_batch(records)
    logger.info(f"  {target_date}: ✓ {inserted:,} rows inserted")
    return inserted


# ── Date helpers ──────────────────────────────────────────────────────────────

def _trading_days(from_date: date, to_date: date) -> list[date]:
    """Return all Mon–Fri dates in [from_date, to_date] inclusive."""
    days = []
    d = from_date
    while d <= to_date:
        if d.weekday() < 5:
            days.append(d)
        d += timedelta(days=1)
    return days


def _already_loaded(db: TimescaleDBClient) -> set[date]:
    """Return flat-file dates already in the DB, identified by source tag 'flatfile:YYYY-MM-DD'."""
    with db.get_connection() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT DISTINCT polygon_request_id FROM options_quotes WHERE source = 'flatfile' AND polygon_request_id IS NOT NULL"
        )
        loaded = set()
        for (val,) in cur.fetchall():
            try:
                loaded.add(date.fromisoformat(val))
            except Exception:
                pass
    logger.info(f"Dates already in DB: {len(loaded)}")
    return loaded


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Bulk-ingest options minute aggregates from Massive flat files")
    parser.add_argument("--from-date", help="Start date YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--to-date",   help="End date YYYY-MM-DD (default: yesterday)")
    parser.add_argument("--days",      type=int, help="Last N trading days (alternative to --from/to-date)")
    parser.add_argument("--workers",   type=int, default=3, help="Parallel download threads (default: 3)")
    parser.add_argument("--force",     action="store_true", help="Re-download dates already in DB")
    args = parser.parse_args()

    tickers = [t.strip() for t in os.getenv("TICKERS", "META,SPY,QQQ").split(",")]
    ticker_set = set(tickers)
    logger.info(f"Tickers: {tickers}")

    yesterday = date.today() - timedelta(days=1)

    if args.days:
        to_date   = yesterday
        from_date = yesterday - timedelta(days=args.days)
    elif args.from_date:
        from_date = date.fromisoformat(args.from_date)
        to_date   = date.fromisoformat(args.to_date) if args.to_date else yesterday
    else:
        from_date = to_date = yesterday

    all_days = _trading_days(from_date, to_date)
    logger.info(f"Date range: {from_date} → {to_date}  ({len(all_days)} trading days)")

    db = TimescaleDBClient(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        database=os.getenv("DB_NAME", "options_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
    )

    if not args.force:
        loaded = _already_loaded(db)
        days_to_fetch = [d for d in all_days if d not in loaded]
        skipped = len(all_days) - len(days_to_fetch)
        if skipped:
            logger.info(f"Skipping {skipped} dates already in DB (use --force to re-download)")
    else:
        days_to_fetch = all_days

    if not days_to_fetch:
        logger.info("Nothing to fetch.")
        db.close()
        return

    logger.info(f"Fetching {len(days_to_fetch)} dates with {args.workers} worker(s)…")

    total = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(ingest_date, d, ticker_set, db): d for d in days_to_fetch}
        for fut in as_completed(futures):
            d = futures[fut]
            try:
                total += fut.result()
            except Exception as e:
                logger.error(f"  {d}: failed — {e}", exc_info=True)

    logger.info(f"✓ Complete — {total:,} total rows inserted across {len(days_to_fetch)} dates")
    db.close()


if __name__ == "__main__":
    main()
