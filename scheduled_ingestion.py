"""
Scheduled Options Data Ingestion
Run this script on a schedule (via Windows Task Scheduler) to continuously ingest data
"""
import os
import sys
import logging
from datetime import datetime, time
from dotenv import load_dotenv
from db_client import TimescaleDBClient
from polygon_ingestion import MassiveOptionsIngester as PolygonOptionsIngester

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('options_ingestion.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ScheduledIngester:
    """Manages scheduled ingestion of options data"""
    
    def __init__(self):
        self.api_key = os.getenv("POLYGON_API_KEY")
        if not self.api_key:
            raise ValueError("POLYGON_API_KEY environment variable not set")
        
        self.db = TimescaleDBClient(
            host=os.getenv("DB_HOST", "localhost"),
            port=int(os.getenv("DB_PORT", 5432)),
            database=os.getenv("DB_NAME", "options_db"),
            user=os.getenv("DB_USER", "postgres"),
            password=os.getenv("DB_PASSWORD", "password")
        )
        
        self.ingester = PolygonOptionsIngester(self.api_key, self.db)
        self.tickers = os.getenv("TICKERS", "META,SPY,QQQ").split(",")
    
    def ingest_latest_snapshots(self) -> dict:
        """
        For each ticker: ingest the options chain expiring today, or the next
        available expiration if today has no listed options.
        """
        logger.info(f"Starting nearest-expiration ingestion for {len(self.tickers)} tickers")
        results = {}
        for ticker in self.tickers:
            try:
                results[ticker] = self.ingester.ingest_nearest_expiration(ticker)
            except Exception as e:
                logger.error(f"Failed to ingest {ticker}: {e}", exc_info=True)
                results[ticker] = 0

        total_inserted = sum(results.values())
        logger.info(f"✓ Ingestion complete: {total_inserted} total quotes inserted")
        return results
    
    def print_statistics(self):
        """Print current database statistics"""
        logger.info("=" * 60)
        logger.info("Database Statistics")
        logger.info("=" * 60)
        
        for ticker in self.tickers:
            try:
                stats = self.db.get_statistics(ticker)
                if stats:
                    logger.info(
                        f"{ticker}: {stats['total_quotes']} quotes "
                        f"({stats['unique_expirations']} expirations, "
                        f"{stats['unique_strikes']} strikes)"
                    )
            except Exception as e:
                logger.warning(f"Could not get stats for {ticker}: {e}")
    
    def run_once(self):
        """Run ingestion once"""
        try:
            logger.info(f"Starting options data ingestion at {datetime.now()}")
            
            # Ingest latest data
            results = self.ingest_latest_snapshots()
            
            # Print statistics
            self.print_statistics()
            
            logger.info("✓ Ingestion cycle completed successfully")
            return True
        
        except Exception as e:
            logger.error(f"✗ Ingestion failed: {e}", exc_info=True)
            return False
        
        finally:
            self.db.close()
    
    def run_continuous(self, interval_minutes: int = 60):
        """
        Run ingestion continuously at specified interval.
        Press Ctrl+C to stop.
        """
        import time
        
        logger.info(f"Starting continuous ingestion (every {interval_minutes} minutes)")
        
        try:
            iteration = 0
            while True:
                iteration += 1
                logger.info(f"\n--- Iteration {iteration} ---")
                
                try:
                    results = self.ingest_latest_snapshots()
                    self.print_statistics()
                except Exception as e:
                    logger.error(f"Error during ingestion: {e}", exc_info=True)
                
                logger.info(f"Next ingestion in {interval_minutes} minutes...")
                time.sleep(interval_minutes * 60)
        
        except KeyboardInterrupt:
            logger.info("Continuous ingestion stopped by user")
        
        finally:
            self.db.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Schedule options data ingestion')
    parser.add_argument(
        '--mode',
        choices=['once', 'continuous', 'backfill'],
        default='once',
        help='once: single snapshot run | continuous: repeat on interval | backfill: load flat-file history'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=60,
        help='Interval in minutes for continuous mode (default: 60)'
    )
    parser.add_argument(
        '--date',
        action='append',
        dest='dates',
        help='Date to backfill YYYY-MM-DD (repeatable). Used with --mode backfill.'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=1,
        help='Number of past trading days to backfill (default: 1 = yesterday). Used with --mode backfill.'
    )

    args = parser.parse_args()

    try:
        if args.mode == 'backfill':
            from flatfile_ingestion import backfill_date, _prev_trading_days
            from datetime import date as _date
            from db_client import TimescaleDBClient

            db = TimescaleDBClient(
                host=os.getenv("DB_HOST", "localhost"),
                port=int(os.getenv("DB_PORT", 5432)),
                database=os.getenv("DB_NAME", "options_db"),
                user=os.getenv("DB_USER", "postgres"),
                password=os.getenv("DB_PASSWORD", "password"),
            )
            tickers = os.getenv("TICKERS", "META,SPY,QQQ").split(",")
            target_dates = (
                [_date.fromisoformat(d) for d in args.dates]
                if args.dates else
                _prev_trading_days(args.days)
            )
            logger.info(f"Backfilling {[str(d) for d in target_dates]} for {tickers}")
            total = sum(backfill_date(d, tickers, db) for d in target_dates)
            logger.info(f"✓ Backfill complete — {total:,} rows inserted")
            db.close()
            sys.exit(0)

        ingester = ScheduledIngester()
        if args.mode == 'once':
            success = ingester.run_once()
            sys.exit(0 if success else 1)
        else:
            ingester.run_continuous(args.interval)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
