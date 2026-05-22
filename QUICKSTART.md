# Quick Start Guide: TimescaleDB + Polygon Options

## 1. Install TimescaleDB

### Option A: Docker (Easiest - Recommended)
```powershell
# Install Docker Desktop from https://www.docker.com/products/docker-desktop

# Pull and run TimescaleDB
docker pull timescale/timescaledb:latest-pg15
docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=password timescale/timescaledb:latest-pg15

# Verify it's running
docker ps  # Should show timescaledb container

# Stop it later with: docker stop timescaledb
# Start again with: docker start timescaledb
```

### Option B: Native PostgreSQL (Windows)
1. Download PostgreSQL 15+ installer: https://www.postgresql.org/download/windows/
2. During installation, remember the password you set
3. Install TimescaleDB extension from: https://docs.timescale.com/self-hosted/latest/install/windows/

## 2. Setup Database Schema

```powershell
# Connect to PostgreSQL (Docker)
docker exec -it timescaledb psql -U postgres

# Or native install - open pgAdmin 4 or psql terminal
psql -U postgres -h localhost

# In the psql terminal, run:
```

Copy and paste the contents of `schema.sql` into your psql terminal, or:

```powershell
# Using psql file import
psql -U postgres -h localhost < schema.sql
```

Verify setup:
```sql
-- In psql
\c options_db
\dt  -- Should show tables: options_quotes, options_chains, options_daily_summary
SELECT * FROM timescaledb_information.hypertables;
```

## 3. Install Python Dependencies

```powershell
cd c:\Users\asdf\source\repos\Options
pip install -r requirements.txt
```

## 4. Get Massive API Key

1. Go to: https://massive.com
2. Sign up for account or use existing account
3. Get your API key from dashboard
4. Set environment variable:

```powershell
# Temporary (current PowerShell session only)
$env:POLYGON_API_KEY = "your_actual_api_key_here"

# Permanent (add to system)
[Environment]::SetEnvironmentVariable("POLYGON_API_KEY", "your_actual_api_key_here", "User")
```

## 5. Test the Setup

```powershell
# Test database connection
python db_client.py

# Expected output:
# ✓ Connected to TimescaleDB at localhost:5432/options_db
# Statistics: {...}
```

## 6. Ingest Data

```powershell
python polygon_ingestion.py
```

## 7. Query Your Data

```python
from db_client import TimescaleDBClient
from datetime import datetime, timedelta

db = TimescaleDBClient()

# Get statistics
stats = db.get_statistics("AAPL")
print(f"Total AAPL quotes: {stats['total_quotes']}")

# Get latest quotes for a ticker
quotes = db.get_latest_quotes("AAPL", limit=10)
for quote in quotes:
    print(f"{quote['option_symbol']}: ${quote['bid']} / ${quote['ask']}")

# Get IV surface (useful for visualization)
iv_surface = db.get_iv_surface("AAPL", "2026-06-18")

# Get price history for an option
prices = db.get_option_prices_for_chain(
    ticker="AAPL",
    expiration_date="2026-06-18",
    time_from=datetime.now() - timedelta(days=7),
    time_to=datetime.now()
)

db.close()
```

## Troubleshooting

### Connection Error: "could not connect to server"
- Check Docker is running: `docker ps`
- Start container: `docker start timescaledb`
- Check host/port in `db_client.py`

### "Permission denied" on schema.sql
- Make sure you're running as Administrator
- Try using: `psql -U postgres < schema.sql`

### Polygon API 401 Error
- Check API key is set correctly: `echo $env:POLYGON_API_KEY`
- Generate new key from Massive dashboard

### "Options contract not found" Error
- The expiration date you requested doesn't exist for that ticker
- Check valid expiration dates: Visit https://polygon.io/docs/options/ and test with your ticker
- Use a more recent expiration date or a different ticker
- Some tickers may have limited options history in Polygon's free tier
- Check the request_id in the error log to investigate on Polygon's support site

### "0 quotes inserted" / No Data Returned
- **Missing API key**: Ensure `POLYGON_API_KEY` environment variable is set correctly
  ```powershell
  echo $env:POLYGON_API_KEY
  ```
- **Subscription tier**: Massive.com subscriptions have different data access levels. Check your plan at https://massive.com/pricing
- **No options available**: Some tickers (especially low-volume or delisted) don't have options
- **API changes**: Verify your API key has proper permissions for options data
- **Enable debug logging**: Debug logs show full API responses to help diagnose issues
- **Test API directly**: 
  ```powershell
  $headers = @{"Authorization" = "Bearer $env:POLYGON_API_KEY"}
  Invoke-RestMethod -Uri "https://api.massive.com/v3/snapshot/options/AAPL?limit=10" -Headers $headers
  ```

### Expiration Date Format Issues
- Use **YYYY-MM-DD** format (e.g., `2026-06-18`, not `06/18/2026`)
- Date must be a valid Friday (or the business day before market holidays)
- Date must be in the future and available on Polygon

### Table already exists error
- Tables already created, you're ready to go
- Or drop and recreate: `DROP DATABASE options_db; CREATE DATABASE options_db;`

## Next Steps

1. **Scale up**: Use cron jobs or scheduled tasks to regularly ingest data
2. **Analysis**: Build queries for Greeks analysis, volatility surfaces, etc.
3. **Visualization**: Use Grafana or Plotly to visualize data
4. **Machine Learning**: Export to pandas for ML models
5. **Real-time**: Set up streaming ingestion for ultra-low latency

## Key Features

✅ **TimescaleDB Advantages**:
- Automatically compresses data older than 7 days (save ~70% storage)
- Auto-retention policy deletes data older than 2 years
- Native time-series optimizations for fast queries
- Handles millions of rows per second ingestion
- Full SQL support (unlike NoSQL solutions)

✅ **Schema Highlights**:
- Greeks already stored (delta, gamma, theta, vega, rho, iv)
- Bid/ask/last prices tracked separately
- Volume and open interest
- Automatic pagination for large result sets
- Efficient indexing for common queries

## Resources

- TimescaleDB Docs: https://docs.timescale.com/
- Polygon Options API: https://polygon.io/docs/options/
- PostgreSQL Docs: https://www.postgresql.org/docs/
