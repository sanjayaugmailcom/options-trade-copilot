# TimescaleDB Options Data Storage

A complete setup for storing and analyzing options data from Massive.com using TimescaleDB, optimized for massive datasets.

## 🚀 Why TimescaleDB?

- **Compression**: Automatically compresses data to ~70% size reduction after 7 days
- **Speed**: Queries millions of rows in milliseconds
- **Retention**: Automatic data deletion policies keep storage manageable
- **Greeks**: Pre-configured storage for delta, gamma, theta, vega, rho, IV
- **SQL**: Full PostgreSQL/SQL support (not a NoSQL limitation)

## 📁 File Structure

```
├── QUICKSTART.md              # Start here - setup guide
├── TIMESCALEDB_SETUP.md       # Installation options (Docker/Native)
├── schema.sql                 # Database schema with hypertables
├── db_client.py               # Database connection & utilities
├── polygon_ingestion.py       # Fetch & ingest data from Massive API
├── advanced_analysis.py       # Analysis queries & patterns
└── requirements.txt           # Python dependencies
```

## ⚡ Quick Start (5 minutes)

1. **Start TimescaleDB with Docker**:
   ```powershell
   docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=password timescale/timescaledb:latest-pg15
   ```

2. **Setup database**:
   ```powershell
   psql -U postgres -h localhost < schema.sql
   ```

3. **Install Python packages**:
   ```powershell
   pip install -r requirements.txt
   ```

4. **Set Massive API key**:
   ```powershell
   $env:POLYGON_API_KEY = "your_key_here"
   ```

5. **Ingest data**:
   ```powershell
   python polygon_ingestion.py
   ```

👉 See [QUICKSTART.md](QUICKSTART.md) for detailed setup instructions.

## 💾 Data Structure

### options_quotes (Main Table)
Real-time options quotes with Greeks. Automatically compressed after 7 days.

| Field | Type | Description |
|-------|------|-------------|
| time | TIMESTAMPTZ | Quote timestamp |
| ticker | TEXT | Underlying symbol (AAPL, SPY, etc) |
| option_symbol | TEXT | Full option symbol (AAPL210917C00150000) |
| strike | DECIMAL | Strike price |
| expiration_date | DATE | Expiration date |
| option_type | CHAR(1) | 'C' (Call) or 'P' (Put) |
| bid/ask/last | DECIMAL | Price levels |
| volume | BIGINT | Quote volume |
| open_interest | BIGINT | Total open interest |
| delta/gamma/theta/vega/rho/iv | DECIMAL | Greeks |

### options_chains (Reference Table)
Static option contract details. Rarely changes.

### options_daily_summary (Aggregated Table)
Daily OHLC summaries for faster analysis.

## 📊 Usage Examples

### Simple Query
```python
from db_client import TimescaleDBClient

db = TimescaleDBClient()

# Get latest AAPL option quotes
quotes = db.get_latest_quotes("AAPL", limit=50)
for q in quotes:
    print(f"{q['option_symbol']}: ${q['bid']} / ${q['ask']}, IV={q['iv']}")

db.close()
```

### IV Surface Analysis
```python
# Get IV smile/skew
iv_surface = db.get_iv_surface("AAPL", "2026-06-18")
for opt in iv_surface:
    print(f"Strike {opt['strike']} {opt['option_type']}: IV={opt['iv']:.2%}")
```

### Advanced Analysis
```python
from advanced_analysis import OptionsAnalyzer

analyzer = OptionsAnalyzer(db)

# IV term structure
term_structure = analyzer.get_iv_term_structure("SPY")

# Put/Call ratio sentiment
pc_ratios = analyzer.get_put_call_ratio("QQQ", "2026-06-18")

# Greeks distribution
greeks = analyzer.get_greek_distribution("TSLA", "2026-06-18")

# Export for ML
ml_data = analyzer.export_for_ml("NVDA", "2026-06-18", "nvda_ml.csv")
```

## 🔧 Common Operations

### Check Database Size
```sql
SELECT 
    pg_size_pretty(pg_database_size('options_db')) as total_size,
    pg_size_pretty(pg_total_relation_size('options_quotes')) as quotes_size;
```

### List Data Coverage
```sql
SELECT ticker, COUNT(*) as records, MIN(time), MAX(time)
FROM options_quotes
GROUP BY ticker
ORDER BY COUNT(*) DESC;
```

### Compression Status
```sql
SELECT 
    hypertable_name,
    compression_enabled,
    total_chunks,
    number_compressed_chunks
FROM timescaledb_information.hypertables;
```

### Continuous Aggregates (Real-time aggregations)
```sql
CREATE MATERIALIZED VIEW daily_iv AS
SELECT 
    DATE_TRUNC('day', time) as day,
    ticker,
    expiration_date,
    AVG(iv) as avg_iv,
    MAX(iv) as max_iv,
    MIN(iv) as min_iv
FROM options_quotes
GROUP BY day, ticker, expiration_date;

-- Query aggregations instantly (pre-computed)
SELECT * FROM daily_iv WHERE day > NOW() - INTERVAL '30 days';
```

## 🎯 Performance Tips

1. **Batch Inserts**: Use `insert_quotes_batch()` with 1000+ rows at a time
2. **Retention Policies**: Keep only needed data (2 year default)
3. **Selective Queries**: Always filter by ticker/date to use indexes
4. **Compression**: Data older than 7 days is auto-compressed
5. **Continuous Aggregates**: Pre-compute daily/weekly summaries for instant queries

## 📈 Typical Data Volumes

For reference, here's storage with TimescaleDB compression:

| Scenario | Records | Storage | Compression Ratio |
|----------|---------|---------|-------------------|
| 1 year, 5 symbols, minute data | ~2.5M | ~500MB | 200:1 |
| 2 years, 100 symbols, hourly | ~1.7M | ~200MB | 250:1 |
| 5 years, 500 symbols, 4-hour | ~2.6M | ~150MB | 300:1 |

Your exact numbers depend on Greeks, bid/ask precision, and retention policies.

## 🤖 Next Steps

1. **Automation**: Set up Windows Task Scheduler to run `polygon_ingestion.py` hourly
2. **Monitoring**: Query database daily to ensure data is flowing
3. **Analysis**: Use `advanced_analysis.py` for options strategies research
4. **Backup**: Regularly backup database with `pg_dump`
5. **Visualization**: Connect to Grafana for real-time dashboards

## 📚 Resources

- [TimescaleDB Documentation](https://docs.timescale.com/)
- [Massive.com Options API](https://massive.com/docs/rest/options/overview)
- [PostgreSQL Hypertables](https://docs.timescale.com/use-timescale/latest/hypertables/)
- [TimescaleDB Compression](https://docs.timescale.com/use-timescale/latest/compression/)

## ❓ FAQ

**Q: Is TimescaleDB free?**  
A: Yes, it's fully open-source PostgreSQL extension. Community edition is free, Cloud has paid tiers.

**Q: How much storage for massive data?**  
A: With compression, typically 50-100x reduction. Most datasets fit in 100GB range.

**Q: Can I use this for real-time trading?**  
A: Yes, but consider adding Redis for ultra-low latency lookups on active options.

**Q: What about failover/HA?**  
A: Set up PostgreSQL replication or use Timescale Cloud for managed HA.

**Q: How do I backup?**  
A: Use `pg_dump` or enable automated backups in Docker/Cloud.

## 📝 License

Your setup, your data. TimescaleDB is Apache 2.0 licensed.
