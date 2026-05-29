"""
One-shot: fetch a single options snapshot and print the full field structure.
Run: python debug_api.py
"""
import os, json, requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("POLYGON_API_KEY", "")
TICKER  = os.getenv("TICKERS", "AAPL").split(",")[0].strip()

headers = {"Authorization": f"Bearer {API_KEY}"}
url = f"https://api.massive.com/v3/snapshot/options/{TICKER}"
resp = requests.get(url, params={"limit": 1}, headers=headers, timeout=15)
print(f"HTTP {resp.status_code}  {url}")

if resp.status_code != 200:
    print(resp.text[:500])
else:
    data = resp.json()
    results = data.get("results", [])
    print(f"status={data.get('status')}  results={len(results)}")

    if results:
        item = results[0]
        print("\n── Top-level keys ──────────────────────────")
        for k, v in item.items():
            if isinstance(v, dict):
                print(f"  {k}: {{ {', '.join(v.keys())} }}")
            else:
                print(f"  {k}: {v!r}")

        # Print every nested dict in full
        print("\n── Full item (pretty) ──────────────────────")
        print(json.dumps(item, indent=2, default=str))
    else:
        print("No results returned — check ticker/API key")
