"""
Probe Massive API for flat file options minute aggregates.
Run: python debug_api.py
"""
import os, json, requests, psycopg2
from datetime import date, timedelta
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("POLYGON_API_KEY", "")
BASE    = "https://api.massive.com"
headers = {"Authorization": f"Bearer {API_KEY}"}
TODAY     = date.today().isoformat()
YESTERDAY = (date.today() - timedelta(days=1)).isoformat()


def db_conn():
    return psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "options_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
    )


def get_sample_contract():
    """Pull the highest-volume option_symbol from the DB."""
    conn = db_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT option_symbol, expiration_date, ticker, volume
        FROM options_quotes
        WHERE volume IS NOT NULL AND volume > 0
        ORDER BY volume DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    if not row:
        cur.execute("SELECT option_symbol, expiration_date, ticker, 0 FROM options_quotes ORDER BY time DESC LIMIT 1")
        row = cur.fetchone()
    conn.close()
    return row


row = get_sample_contract()
if not row:
    print("No contracts in DB — run ingestion first.")
    raise SystemExit(1)

symbol, exp_date, ticker, volume = row
exp_str = str(exp_date)
print(f"\nSample contract : {symbol}")
print(f"Ticker          : {ticker}")
print(f"Expiry          : {exp_str}")
print(f"Volume          : {volume}")
print(f"Today           : {TODAY}")
print(f"Yesterday       : {YESTERDAY}")

# Flat file candidate URLs to probe
candidates = [
    # Polygon-style CDN flat file
    ("CDN flatfiles — yesterday gz",
     f"https://cdn.massive.com/flatfiles/options/minute_aggs/{YESTERDAY}.csv.gz", {}),
    ("CDN flatfiles — today gz",
     f"https://cdn.massive.com/flatfiles/options/minute_aggs/{TODAY}.csv.gz", {}),
    # API-served flat file endpoints
    ("API v1 flat-files listing",
     f"{BASE}/v1/flat-files/options/minute-aggregates", {}),
    ("API v1 flatfiles listing (underscore)",
     f"{BASE}/v1/flatfiles/options/minute-aggregates", {}),
    ("API v1 flatfiles with date",
     f"{BASE}/v1/flatfiles/options/minute-aggregates/{YESTERDAY}", {}),
    # Presigned S3 URL pattern
    ("API v1 download presigned URL",
     f"{BASE}/v1/flatfiles/options/minute-aggregates/download",
     {"date": YESTERDAY}),
    # Some providers serve via /v1/reference/bulk
    ("API bulk reference",
     f"{BASE}/v1/bulk/options/minute-aggregates",
     {"date": YESTERDAY}),
]

for label, url, params in candidates:
    print(f"\n{'='*62}")
    print(f"  {label}")
    print(f"  {url}")
    if params:
        print(f"  params={params}")
    print(f"{'='*62}")
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10, allow_redirects=False)
        ct = resp.headers.get("Content-Type", "?")
        print(f"  HTTP {resp.status_code}  Content-Type: {ct}")
        if resp.status_code in (301, 302, 307, 308):
            print(f"  Redirect → {resp.headers.get('Location')}")
        elif resp.status_code == 200:
            if "json" in ct:
                print(json.dumps(resp.json(), indent=2, default=str)[:800])
            else:
                print(f"  Binary response ({len(resp.content)} bytes) — first 200 bytes:")
                print(resp.content[:200])
        else:
            print(f"  Body: {resp.text[:400]}")
    except Exception as e:
        print(f"  Error: {e}")
