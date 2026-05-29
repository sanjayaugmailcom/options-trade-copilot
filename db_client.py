"""
TimescaleDB Connection & Management Utilities for Options Data
"""
import os
from typing import Optional, List, Dict, Any
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
from psycopg2.pool import SimpleConnectionPool
from contextlib import contextmanager
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TimescaleDBClient:
    """Manages connections and operations for TimescaleDB"""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "options_db",
        user: str = "postgres",
        password: str = "password",
        min_conn: int = 1,
        max_conn: int = 10
    ):
        """Initialize TimescaleDB client with connection pool"""
        self.connection_string = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        
        try:
            self.pool = SimpleConnectionPool(
                min_conn,
                max_conn,
                host=host,
                port=port,
                database=database,
                user=user,
                password=password
            )
            logger.info(f"✓ Connected to TimescaleDB at {host}:{port}/{database}")
        except Exception as e:
            logger.error(f"✗ Failed to connect to TimescaleDB: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        conn = self.pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            self.pool.putconn(conn)
    
    def insert_quotes_batch(
        self, 
        quotes: List[Dict[str, Any]]
    ) -> int:
        """
        Insert multiple option quotes efficiently.
        
        Args:
            quotes: List of quote dicts with keys:
                - time, ticker, option_symbol, strike, expiration_date, option_type
                - bid, ask, last, volume, open_interest
                - delta, gamma, theta, vega, rho, iv (optional)
                - source, polygon_request_id
        
        Returns:
            Number of rows inserted
        """
        if not quotes:
            return 0
        
        columns = [
            'time', 'ticker', 'option_symbol', 'strike', 'expiration_date',
            'option_type', 'bid', 'ask', 'last', 'volume', 'open_interest',
            'delta', 'gamma', 'theta', 'vega', 'rho', 'iv', 'source', 'polygon_request_id'
        ]
        
        values = []
        for quote in quotes:
            values.append(tuple(quote.get(col) for col in columns))
        
        query = f"""
            INSERT INTO options_quotes ({', '.join(columns)})
            VALUES %s
            ON CONFLICT DO NOTHING
        """
        
        with self.get_connection() as conn:
            cur = conn.cursor()
            execute_values(cur, query, values, page_size=1000)
            inserted = cur.rowcount
            logger.info(f"✓ Inserted {inserted} quotes")
            return inserted
    
    def get_latest_quotes(
        self,
        ticker: str,
        expiration_date: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get latest option quotes for a ticker"""
        query = """
            SELECT * FROM options_quotes
            WHERE ticker = %s
        """
        params = [ticker]
        
        if expiration_date:
            query += " AND expiration_date = %s"
            params.append(expiration_date)
        
        query += """
            ORDER BY time DESC
            LIMIT %s
        """
        params.append(limit)
        
        with self.get_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            return cur.fetchall()
    
    def get_option_prices_for_chain(
        self,
        ticker: str,
        expiration_date: str,
        time_from: datetime,
        time_to: datetime
    ) -> List[Dict]:
        """Get all option prices for a specific expiration date over time period"""
        query = """
            SELECT 
                time, strike, option_type, bid, ask, last,
                delta, gamma, theta, vega, iv, volume
            FROM options_quotes
            WHERE ticker = %s
                AND expiration_date = %s
                AND time BETWEEN %s AND %s
            ORDER BY time DESC, strike, option_type
        """
        
        with self.get_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, [ticker, expiration_date, time_from, time_to])
            return cur.fetchall()
    
    def get_iv_surface(
        self,
        ticker: str,
        expiration_date: str,
        as_of_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Get IV surface (strike vs IV) for visualization"""
        query = """
            SELECT DISTINCT ON (strike, option_type)
                strike, option_type, iv, bid, ask, volume
            FROM options_quotes
            WHERE ticker = %s AND expiration_date = %s
        """
        params = [ticker, expiration_date]
        
        if as_of_time:
            query += " AND time <= %s"
            params.append(as_of_time)
        
        query += " ORDER BY strike, option_type, time DESC"
        
        with self.get_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, params)
            return cur.fetchall()
    
    def get_statistics(self, ticker: str) -> Dict:
        """Get statistics for a ticker"""
        query = """
            SELECT
                ticker,
                COUNT(*) as total_quotes,
                MIN(time) as first_quote,
                MAX(time) as last_quote,
                COUNT(DISTINCT expiration_date) as unique_expirations,
                COUNT(DISTINCT strike) as unique_strikes,
                AVG(volume)::BIGINT as avg_volume
            FROM options_quotes
            WHERE ticker = %s
            GROUP BY ticker
        """
        
        with self.get_connection() as conn:
            cur = conn.cursor(cursor_factory=RealDictCursor)
            cur.execute(query, [ticker])
            result = cur.fetchone()
            return dict(result) if result else {}
    
    def delete_daily_records(
        self,
        ticker: str,
        expiration_date: str,
        ny_date,  # datetime.date in New York timezone
    ) -> int:
        """Delete all records for ticker+expiration ingested on a given NY calendar day."""
        query = """
            DELETE FROM options_quotes
            WHERE ticker = %s
              AND expiration_date = %s
              AND (time AT TIME ZONE 'America/New_York')::date = %s
        """
        with self.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, [ticker, expiration_date, ny_date])
            deleted = cur.rowcount
            logger.info(
                f"Deleted {deleted} stale records for {ticker} {expiration_date} "
                f"on {ny_date} (NY) before re-ingestion"
            )
            return deleted

    def close(self):
        """Close all connections in the pool"""
        if self.pool:
            self.pool.closeall()
            logger.info("✓ Connection pool closed")


# Example usage
if __name__ == "__main__":
    # Initialize client
    db = TimescaleDBClient(
        host="localhost",
        port=5432,
        database="options_db",
        user="postgres",
        password="password"
    )
    
    # Get statistics
    stats = db.get_statistics("AAPL")
    print(f"Statistics: {stats}")
    
    # Get latest quotes
    quotes = db.get_latest_quotes("AAPL", limit=10)
    print(f"Latest quotes: {quotes}")
    
    db.close()
