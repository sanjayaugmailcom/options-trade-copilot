"""
Massive.com Options Data Ingestion for TimescaleDB
Fetches options data from Massive API and stores in TimescaleDB
"""
import requests
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging
from db_client import TimescaleDBClient

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
    
    def fetch_options_with_greeks(
        self,
        ticker: str,
        expiration_date: str
    ) -> List[Dict]:
        """
        Fetch options data with Greeks for a specific expiration date.
        
        Note: Massive endpoint returns all expirations, so we filter by expiration_date
        
        https://massive.com/docs/rest/options/overview#available-endpoints
        Endpoint: GET /v3/snapshot/options/{underlyingAsset}
        """
        # Convert date format if needed (YYYY-MM-DD)
        try:
            exp_obj = datetime.strptime(expiration_date, "%Y-%m-%d")
            formatted_exp = exp_obj.strftime("%Y-%m-%d")
        except ValueError:
            logger.error(f"Invalid expiration date format: {expiration_date}. Use YYYY-MM-DD")
            return []
        
        url = f"{self.BASE_URL}/v3/snapshot/options/{ticker}"
        params = {
            "limit": 250  # Max per request
        }
        
        all_results = []
        
        try:
            while url:
                logger.info(f"Requesting: {url}")
                response = self.session.get(url, params=params, headers=self.headers)
                logger.info(f"Response status code: {response.status_code}")
                
                # Handle 404 specifically
                if response.status_code == 404:
                    logger.error(
                        f"Ticker {ticker} not found or no options available. "
                        f"Endpoint: {url}"
                    )
                    return []
                
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"Response data keys: {list(data.keys())}")
                
                if data.get("status") != "OK":
                    error_msg = data.get("message", "Unknown error")
                    request_id = data.get("request_id", "N/A")
                    logger.warning(
                        f"Massive API error for {ticker}/{formatted_exp}: {error_msg} "
                        f"(request_id: {request_id})"
                    )
                    break
                
                results = data.get("results", [])
                logger.info(f"Got {len(results)} results from API for {ticker}")
                
                # Log only the first few keys to inspect the response schema
                if results and isinstance(results[0], dict):
                    first_keys = list(results[0].keys())[:5]
                    logger.info(f"First result keys: {first_keys}")
                    first_contract = results[0]
                    if isinstance(first_contract.get("details"), dict):
                        details_keys = list(first_contract["details"].keys())[:5]
                        logger.info(f"First result.details keys: {details_keys}")
                    if isinstance(first_contract.get("day"), dict):
                        day_keys = list(first_contract["day"].keys())[:5]
                        logger.info(f"First result.day keys: {day_keys}")
                elif results:
                    logger.info("First result is not a dict")
                else:
                    logger.info("No results returned by API")
                
                # Filter results by expiration date since Massive returns all expirations
                filtered_results = []
                for r in results:
                    exp_date = (
                        (r.get("details") or {}).get("expiration_date") or
                        (r.get("details") or {}).get("expiration") or
                        (r.get("details") or {}).get("expiry_date") or
                        (r.get("details") or {}).get("expiry") or
                        (r.get("day") or {}).get("expiration_date") or
                        (r.get("day") or {}).get("expiration") or
                        (r.get("day") or {}).get("expiry_date") or
                        (r.get("day") or {}).get("expiry") or
                        r.get("expiration_date") or
                        r.get("expiration") or
                        r.get("expiry_date") or
                        r.get("expiry")
                    )
                    if exp_date == formatted_exp:
                        filtered_results.append(r)
                
                logger.info(f"Filtered to {len(filtered_results)} results for expiration {formatted_exp}")
                all_results.extend(filtered_results)
                
                # Handle pagination
                next_url = data.get("next_url")
                if next_url:
                    logger.info(f"Found next_url, fetching next page...")
                    url = next_url
                    params = {}  # URL already includes params
                else:
                    break
            
            return all_results
        
        except requests.RequestException as e:
            logger.error(f"Failed to fetch options chain for {ticker}/{formatted_exp}: {e}")
            return []
    
    def transform_quote_to_db_format(
        self,
        ticker: str,
        quote: Dict,
        request_id: Optional[str] = None
    ) -> Dict:
        """Transform Massive option quote format to database format"""
        
        details = quote.get("details", {}) or {}
        day = quote.get("day", {}) or {}
        greeks = quote.get("greeks", {}) or {}
        
        # Option symbol may be nested under details
        option_symbol = (
            quote.get("option_symbol") or
            details.get("contract_symbol") or
            details.get("symbol") or
            details.get("contract_name") or
            quote.get("ticker")
        )
        
        expiration_date_str = (
            details.get("expiration_date") or
            details.get("expiration") or
            details.get("expiry_date") or
            details.get("expiry") or
            quote.get("expiration_date") or
            quote.get("expiration") or
            quote.get("expiry_date") or
            quote.get("expiry")
        )
        
        if not expiration_date_str:
            logger.debug("Missing expiration date for quote, skipping")
            return None
        
        try:
            expiration_date = datetime.strptime(expiration_date_str, "%Y-%m-%d").date()
        except Exception as e:
            logger.debug(f"Could not parse expiration date {expiration_date_str}: {e}")
            return None
        
        strike = details.get("strike_price") or details.get("strike") or quote.get("strike")
        try:
            if strike is not None:
                strike = float(strike)
        except Exception:
            logger.debug(f"Could not parse strike price {strike}")
            return None
        
        option_type = (
            (details.get("contract_type") or details.get("option_type") or quote.get("option_type") or "")
            .upper()
        )
        if option_type.startswith("C"):
            option_type = "C"
        elif option_type.startswith("P"):
            option_type = "P"
        else:
            option_type = option_type[:1]
        
        if not option_symbol:
            option_symbol = f"{ticker}-{expiration_date.strftime('%Y%m%d')}-{option_type or 'X'}-{strike}"
        
        time_str = day.get("last_updated") or quote.get("last_updated") or datetime.utcnow().isoformat()
        try:
            time = datetime.fromisoformat(time_str)
        except Exception:
            time = datetime.utcnow()
        
        bid = quote.get("bid") or day.get("bid")
        ask = quote.get("ask") or day.get("ask")
        last = quote.get("last") or day.get("close") or day.get("last")
        volume = quote.get("volume") or day.get("volume")
        open_interest = quote.get("open_interest") or quote.get("open_interest") or day.get("open_interest")
        
        return {
            "time": time,
            "ticker": ticker,
            "option_symbol": option_symbol,
            "strike": strike,
            "expiration_date": expiration_date,
            "option_type": option_type,
            "bid": bid,
            "ask": ask,
            "last": last,
            "volume": volume,
            "open_interest": open_interest,
            "delta": greeks.get("delta"),
            "gamma": greeks.get("gamma"),
            "theta": greeks.get("theta"),
            "vega": greeks.get("vega"),
            "rho": greeks.get("rho"),
            "iv": greeks.get("iv") or quote.get("implied_volatility"),
            "source": "massive",
            "polygon_request_id": request_id
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
        """Fetch and ingest all options for a specific expiration date"""
        logger.info(f"Fetching {ticker} options expiring {expiration_date}...")
        
        quotes = self.fetch_options_with_greeks(ticker, expiration_date)
        if not quotes:
            logger.warning(f"No quotes found for {ticker} {expiration_date}")
            return 0
        
        # Transform quotes
        db_quotes = []
        for quote in quotes:
            db_quote = self.transform_quote_to_db_format(ticker, quote)
            if db_quote:
                db_quotes.append(db_quote)
        
        # Insert into database
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
    # Configuration
    POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "your_api_key_here")
    
    # Initialize database and ingester
    db = TimescaleDBClient()
    ingester = MassiveOptionsIngester(POLYGON_API_KEY, db)
    
    try:
        # Example 1: Ingest latest snapshot
        print("\n=== Ingesting Latest Snapshots ===")
        results = ingester.ingest_multiple_tickers(["AAPL", "SPY", "QQQ"])
        for ticker, count in results.items():
            print(f"{ticker}: {count} quotes inserted")
        
        # Example 2: Ingest specific expiration
        print("\n=== Ingesting Specific Expiration ===")
        count = ingester.ingest_options_chain("AAPL", "2026-06-18")
        print(f"AAPL 2026-06-18: {count} quotes inserted")
        
        # Example 3: Query what we stored
        print("\n=== Database Statistics ===")
        stats = db.get_statistics("AAPL")
        print(f"AAPL Stats: {stats}")
        
        print("\n=== Latest Quotes ===")
        quotes = db.get_latest_quotes("AAPL", limit=5)
        for quote in quotes:
            print(f"  {quote['option_symbol']}: bid={quote['bid']}, ask={quote['ask']}, iv={quote['iv']}")
    
    finally:
        db.close()
