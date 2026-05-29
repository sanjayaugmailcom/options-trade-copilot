"""
Massive.com Options Data Ingestion for TimescaleDB
Fetches options data from Massive API and stores in TimescaleDB
"""
import requests
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict, Optional
import logging
from db_client import TimescaleDBClient

NY_TZ = ZoneInfo("America/New_York")


def ny_today():
    """Return today's date in New York time."""
    return datetime.now(tz=NY_TZ).date()

logging.basicConfig(
    level=logging.DEBUG,  # Enable debug logging to see API response details
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)


class MassiveOptionsIngester:
    """Fetches options data from Massive.com and stores in TimescaleDB"""
    
    BASE_URL = "https://api.massive.com"
    
    def __init__(self, api_key: str, db: TimescaleDBClient):
        """
        Initialize Massive ingester.
        
        Args:
            api_key: Your Massive.com API key
            db: TimescaleDBClient instance
        """
        self.api_key = api_key
        self.db = db
        self.session = requests.Session()
        # Massive uses header-based auth
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def fetch_options_snapshots(
        self,
        ticker: str,
        order: str = "desc",
        limit: int = 100
    ) -> List[Dict]:
        """
        Fetch latest options snapshot (quotes) for a ticker.
        
        https://massive.com/docs/rest/options/overview#available-endpoints
        Endpoint: GET /v3/snapshot/options/{underlyingAsset}
        """
        url = f"{self.BASE_URL}/v3/snapshot/options/{ticker}"
        params = {
            "order": order,
            "limit": limit
        }
        
        try:
            response = self.session.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            logger.debug(f"Snapshot response status: {response.status_code}, data keys: {data.keys()}")
            
            if data.get("status") != "OK":
                error_msg = data.get("message", "Unknown error")
                request_id = data.get("request_id", "N/A")
                logger.warning(
                    f"Massive API error for {ticker}: {error_msg} "
                    f"(request_id: {request_id})"
                )
                return []
            
            results = data.get("results", [])
            logger.debug(f"Snapshot returned {len(results)} results for {ticker}")
            return results
        
        except requests.RequestException as e:
            logger.error(f"Failed to fetch snapshot for {ticker}: {e}")
            return []
    
    def get_nearest_expiration(self, ticker: str) -> Optional[str]:
        """
        Return today's expiration date if options exist, otherwise the next
        available expiration date on or after today.
        Returns a YYYY-MM-DD string, or None if nothing found.
        """
        today = ny_today().isoformat()
        url = f"{self.BASE_URL}/v3/snapshot/options/{ticker}"

        # Try today first
        try:
            resp = self.session.get(
                url,
                params={"expiration_date": today, "limit": 1},
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()
            if data.get("status") == "OK" and data.get("results"):
                logger.info(f"Found options expiring today ({today}) for {ticker}")
                return today
        except requests.RequestException as e:
            logger.warning(f"Error checking today's expiration for {ticker}: {e}")

        # Fall back to nearest future expiration
        try:
            resp = self.session.get(
                url,
                params={"expiration_date.gte": today, "order": "asc", "limit": 1},
                headers=self.headers,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                exp = (results[0].get("details") or {}).get("expiration_date")
                if exp:
                    logger.info(f"Nearest expiration for {ticker}: {exp}")
                    return exp
        except requests.RequestException as e:
            logger.warning(f"Error finding nearest expiration for {ticker}: {e}")

        logger.warning(f"Could not determine target expiration for {ticker}")
        return None

    def fetch_options_with_greeks(
        self,
        ticker: str,
        expiration_date: str
    ) -> List[Dict]:
        """
        Fetch the full options chain for a specific expiration date.
        Uses server-side expiration_date filter and paginates automatically.
        Endpoint: GET /v3/snapshot/options/{underlyingAsset}
        """
        try:
            datetime.strptime(expiration_date, "%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid expiration date format: {expiration_date}. Use YYYY-MM-DD")
            return []

        url = f"{self.BASE_URL}/v3/snapshot/options/{ticker}"
        params = {"expiration_date": expiration_date, "limit": 250}
        all_results = []

        try:
            while url:
                logger.info(f"Fetching {ticker} {expiration_date}: {url}")
                response = self.session.get(url, params=params, headers=self.headers)

                if response.status_code == 404:
                    logger.error(f"Ticker {ticker} not found. Endpoint: {url}")
                    return []

                response.raise_for_status()
                data = response.json()

                if data.get("status") != "OK":
                    logger.warning(
                        f"API error for {ticker}/{expiration_date}: "
                        f"{data.get('message', 'Unknown error')}"
                    )
                    break

                results = data.get("results", [])
                logger.info(f"  page: {len(results)} results")
                all_results.extend(results)

                next_url = data.get("next_url")
                if next_url:
                    url = next_url
                    params = {}
                else:
                    break

            logger.info(f"Total fetched for {ticker} {expiration_date}: {len(all_results)}")
            return all_results

        except requests.RequestException as e:
            logger.error(f"Failed to fetch chain for {ticker}/{expiration_date}: {e}")
            return []

    def ingest_nearest_expiration(self, ticker: str) -> int:
        """
        Auto-detect today's expiration (or the next available one) and ingest
        the full options chain for that date.
        """
        expiration_date = self.get_nearest_expiration(ticker)
        if not expiration_date:
            logger.warning(f"No upcoming expiration found for {ticker}, skipping")
            return 0
        logger.info(f"Target expiration for {ticker}: {expiration_date}")
        return self.ingest_options_chain(ticker, expiration_date)
    
    def transform_quote_to_db_format(
        self,
        ticker: str,
        quote: Dict,
        request_id: Optional[str] = None
    ) -> Dict:
        """Transform Massive option quote format to database format"""
        
        details         = quote.get("details", {})    or {}
        day             = quote.get("day", {})         or {}
        greeks          = quote.get("greeks", {})      or {}
        last_quote_data = quote.get("last_quote", {})  or {}
        last_trade_data = quote.get("last_trade", {})  or {}

        # details.ticker is the OCC symbol, e.g. "O:AAPL281215C00060000"
        option_symbol = (
            details.get("ticker") or
            quote.get("option_symbol") or
            quote.get("ticker")
        )

        expiration_date_str = details.get("expiration_date") or quote.get("expiration_date")
        if not expiration_date_str:
            logger.debug("Missing expiration date, skipping")
            return None
        try:
            expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d").date()
        except Exception as e:
            logger.debug(f"Could not parse expiration date {expiration_date_str}: {e}")
            return None

        strike = details.get("strike_price") or details.get("strike") or quote.get("strike")
        try:
            strike = float(strike) if strike is not None else None
        except Exception:
            logger.debug(f"Could not parse strike {strike}")
            return None

        option_type = (
            details.get("contract_type") or details.get("option_type") or quote.get("option_type") or ""
        ).upper()
        option_type = "C" if option_type.startswith("C") else ("P" if option_type.startswith("P") else option_type[:1])

        if not option_symbol:
            option_symbol = f"{ticker}-{expiration_date.strftime('%Y%m%d')}-{option_type or 'X'}-{strike}"

        # last_updated is Unix nanoseconds (int), not an ISO string
        ts_ns = day.get("last_updated") or quote.get("last_updated")
        if ts_ns and isinstance(ts_ns, (int, float)) and ts_ns > 0:
            try:
                record_time = datetime.fromtimestamp(ts_ns / 1e9, tz=timezone.utc)
            except Exception:
                record_time = datetime.now(tz=timezone.utc)
        else:
            record_time = datetime.now(tz=timezone.utc)

        def _get(*sources):
            for v in sources:
                if v is not None:
                    return v
            return None

        # bid/ask come from last_quote when present (liquid options only)
        bid  = _get(last_quote_data.get("bid"),  quote.get("bid"))
        ask  = _get(last_quote_data.get("ask"),  quote.get("ask"))
        # last price is day.close (most recent trade)
        last = _get(last_trade_data.get("price"), day.get("close"), day.get("last"), quote.get("last"))
        # volume and OI
        volume        = _get(day.get("volume"),        quote.get("volume"))
        open_interest = _get(quote.get("open_interest"), day.get("open_interest"))
        # iv lives at the top level as implied_volatility
        iv = _get(quote.get("implied_volatility"), greeks.get("iv"))

        return {
            "time":               record_time,
            "ticker":             ticker,
            "option_symbol":      option_symbol,
            "strike":             strike,
            "expiration_date":    expiration_date,
            "option_type":        option_type,
            "bid":                bid,
            "ask":                ask,
            "last":               last,
            "volume":             volume,
            "open_interest":      open_interest,
            "delta":              greeks.get("delta"),
            "gamma":              greeks.get("gamma"),
            "theta":              greeks.get("theta"),
            "vega":               greeks.get("vega"),
            "rho":                greeks.get("rho"),
            "iv":                 iv,
            "source":             "massive",
            "polygon_request_id": request_id,
        }
    
    def ingest_ticker_snapshot(self, ticker: str) -> int:
        """Fetch and ingest latest options snapshot for a ticker"""
        logger.info(f"Fetching options snapshot for {ticker}...")
        
        quotes = self.fetch_options_snapshots(ticker)
        if not quotes:
            logger.warning(f"No quotes found for {ticker}")
            return 0
        
        # Transform quotes
        db_quotes = []
        for quote in quotes:
            db_quote = self.transform_quote_to_db_format(ticker, quote)
            if db_quote:
                db_quotes.append(db_quote)
        
        # Insert into database
        inserted = self.db.insert_quotes_batch(db_quotes)
        logger.info(f"✓ Ingested {inserted} quotes for {ticker}")
        return inserted
    
    def ingest_options_chain(
        self,
        ticker: str,
        expiration_date: str
    ) -> int:
        """
        Fetch and ingest all options for a specific expiration date.
        If records for this ticker+expiration already exist for today (NY time),
        they are replaced so repeat runs on the same day stay current.
        """
        logger.info(f"Fetching {ticker} options expiring {expiration_date}...")

        quotes = self.fetch_options_with_greeks(ticker, expiration_date)
        if not quotes:
            logger.warning(f"No quotes found for {ticker} {expiration_date}")
            return 0

        db_quotes = [
            q for q in (self.transform_quote_to_db_format(ticker, r) for r in quotes)
            if q
        ]

        # Delete today's existing records (NY time) before re-inserting
        self.db.delete_daily_records(ticker, expiration_date, ny_today())

        inserted = self.db.insert_quotes_batch(db_quotes)
        logger.info(f"✓ Ingested {inserted} quotes for {ticker} {expiration_date}")
        return inserted
    
    def ingest_multiple_tickers(
        self,
        tickers: List[str],
        expiration_dates: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """Ingest data for multiple tickers and expiration dates"""
        results = {}
        
        for ticker in tickers:
            if expiration_dates:
                # Ingest specific expirations
                for exp_date in expiration_dates:
                    key = f"{ticker}_{exp_date}"
                    results[key] = self.ingest_options_chain(ticker, exp_date)
            else:
                # Ingest latest snapshot
                results[ticker] = self.ingest_ticker_snapshot(ticker)
        
        return results


# Example usage
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    # Configuration
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")
    
    # Initialize database and ingester
    db = TimescaleDBClient()
    ingester = MassiveOptionsIngester(POLYGON_API_KEY, db)
    
    tickers = os.getenv("TICKERS", "AAPL,SPY,QQQ").split(",")

    try:
        print(f"\n=== Ingesting nearest expiration for: {tickers} ===")
        for ticker in tickers:
            ticker = ticker.strip()
            exp = ingester.get_nearest_expiration(ticker)
            if exp:
                count = ingester.ingest_options_chain(ticker, exp)
                print(f"  {ticker} {exp}: {count} quotes inserted")
            else:
                print(f"  {ticker}: no upcoming expiration found")

        print("\n=== Database Statistics ===")
        for ticker in tickers:
            ticker = ticker.strip()
            stats = db.get_statistics(ticker)
            if stats:
                print(f"  {ticker}: {stats['total_quotes']} quotes, "
                      f"{stats['unique_expirations']} expirations, "
                      f"{stats['unique_strikes']} strikes")

        print("\n=== Latest Quotes ===")
        quotes = db.get_latest_quotes(tickers[0].strip(), limit=5)
        for quote in quotes:
            print(f"  {quote['option_symbol']}: last={quote['last']}, iv={quote['iv']}, delta={quote['delta']}")

    finally:
        db.close()
