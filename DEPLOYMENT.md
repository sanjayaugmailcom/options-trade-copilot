# Deployment & Troubleshooting Guide

## 🐳 Docker Deployment (Recommended for Development)

### One-liner to start everything:
```powershell
docker run -d `
  --name timescaledb `
  -p 5432:5432 `
  -e POSTGRES_PASSWORD=password `
  -v timescale_data:/var/lib/postgresql/data `
  timescale/timescaledb:latest-pg15
```

### Verify container is running:
```powershell
docker ps
docker logs timescaledb  # View logs
docker exec timescaledb psql -U postgres -c "SELECT version();"
```

### Stop/Start/Remove:
```powershell
docker stop timescaledb
docker start timescaledb
docker rm timescaledb  # Remove container (keeps volume)
docker volume rm timescale_data  # Remove data
```

---

## 🖥️ Windows Task Scheduler Setup (For Production)

### Step 1: Create Python Virtual Environment
```powershell
cd c:\Users\asdf\source\repos\Options
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Step 2: Test the ingestion script
```powershell
python scheduled_ingestion.py --mode once
```

Should see output like:
```
✓ Connected to TimescaleDB at localhost:5432/options_db
Starting snapshot ingestion for 10 tickers
✓ Inserted 245 quotes
... (repeats for each ticker)
```

### Step 3: Set Environment Variable
```powershell
# Open Command Prompt as Administrator
setx POLYGON_API_KEY "your_actual_key_here"

# Verify
echo %POLYGON_API_KEY%
```

### Step 4: Create Task Scheduler Task
1. Open **Task Scheduler** (Win+R → `taskschd.msc`)
2. Click **Create Basic Task**
3. Fill in:
   - **Name**: `Options Data Ingestion`
   - **Description**: `Hourly ingestion from Polygon API`
4. **Trigger** tab:
   - Choose `Daily`
   - Set time to `00:00` (midnight)
   - Check **Repeat task every**: `1 hour`
   - Check **Enabled**
5. **Action** tab:
   - **Program/script**: `python.exe`
   - **Add arguments**: `scheduled_ingestion.py --mode once`
   - **Start in**: `c:\Users\asdf\source\repos\Options`
6. **Conditions** tab:
   - Uncheck "Stop if computer on battery"
7. Click **OK**

### Verify task is working:
```powershell
# Run task manually to test
Get-ScheduledTask -TaskName "Options Data Ingestion" | Start-ScheduledTask

# Check logs
Get-EventLog -LogName System | Select-Object -First 20 TimeGenerated, Source, EventID

# Or check our log file
Get-Content ingestion_*.log -Tail 20
```

---

## 🔍 Troubleshooting

### Connection Issues

**"could not connect to server"**
- Check Docker is running: `docker ps`
- Check port 5432 is available: `Get-NetTCPConnection -LocalPort 5432`
- Verify TimescaleDB container: `docker logs timescaledb`

**"FATAL: remaining connection slots are reserved"**
- Connection pool exhausted
- Solution: Increase `max_conn` in `db_client.py`
- Or: Close previous connections before opening new ones

### Data Issues

**"Permission denied for schema check"**
- Make sure you created the database as postgres user
- Try: `psql -U postgres -h localhost < schema.sql`

**"Duplicate key value violates unique constraint"**
- This is okay! The code handles it with `ON CONFLICT DO NOTHING`
- Means data was already inserted

**"No quotes found for ticker"**
- Check your Polygon API key is valid
- Verify ticker is spelled correctly
- Check API rate limits (free tier has limits)

### Polygon API Issues

**401 Unauthorized**
```powershell
# Verify your API key
$env:POLYGON_API_KEY
# Should output your key, not blank
```

**429 Too Many Requests**
- You hit rate limit (free tier: 120 req/min)
- Solution: Increase `interval_minutes` in scheduled_ingestion.py
- Or upgrade to paid plan

**Empty results but 200 OK**
- Valid API key but no data available for that ticker
- Try a more liquid ticker like AAPL or SPY

### Performance Issues

**Slow queries**
```sql
-- Check indexes
SELECT * FROM pg_stat_user_indexes WHERE idx_blks_read > 0;

-- Reindex if needed
REINDEX TABLE options_quotes;
```

**High memory usage**
```sql
-- Check table sizes
SELECT 
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename))
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Force compression of old data
SELECT compress_chunk(i) FROM show_chunks('options_quotes') i 
WHERE i NOT IN (
    SELECT i FROM show_chunks('options_quotes', INTERVAL '7 days')
);
```

---

## 📊 Monitoring & Health Checks

### Daily health check script:
```python
from db_client import TimescaleDBClient
from datetime import datetime

db = TimescaleDBClient()

# Check data freshness
query = """
SELECT 
    ticker,
    MAX(time) as last_update,
    COUNT(*) as quote_count,
    NOW() - MAX(time) as age
FROM options_quotes
GROUP BY ticker
ORDER BY MAX(time) DESC;
"""

with db.get_connection() as conn:
    cur = conn.cursor()
    cur.execute(query)
    for ticker, last_update, count, age in cur.fetchall():
        print(f"{ticker}: {count} quotes, updated {age.total_seconds()/3600:.1f}h ago")
        if age.total_seconds() > 86400:  # > 24 hours
            print(f"  ⚠️  WARNING: No recent data for {ticker}")

db.close()
```

### Key metrics to monitor:
- **Data freshness**: Last update for each ticker (should be < 24h)
- **Database size**: Should grow ~50MB-100MB per month (with compression)
- **Insert rate**: Should be > 100 rows/second
- **Query latency**: 99th percentile < 1 second

---

## 🔐 Security Considerations

### API Key Management
```powershell
# NEVER hardcode API keys
# Use environment variables:
$env:POLYGON_API_KEY = "..."

# Or environment file (add to .gitignore):
# .env file with POLYGON_API_KEY=...
```

### Database Security
```sql
-- Create read-only user for analytics
CREATE USER analytics WITH PASSWORD 'strong_password';
GRANT CONNECT ON DATABASE options_db TO analytics;
GRANT USAGE ON SCHEMA public TO analytics;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics;

-- Revoke write access
REVOKE INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public FROM analytics;
```

### Network Security
- Don't expose port 5432 to internet
- Use SSH tunnel if accessing remotely:
  ```powershell
  ssh -L 5432:localhost:5432 user@remote_server
  ```

---

## 🚀 Scaling to Production

### High-availability setup:
1. **Primary/Replica**: Set up PostgreSQL replication
2. **Automated backups**: Use `pg_basebackup` or cloud backups
3. **Monitoring**: Install pgAdmin or Grafana
4. **Load balancing**: Use pgBouncer for connection pooling

### Recommended cloud options:
- **Timescale Cloud**: Managed TimescaleDB (recommended)
- **AWS RDS**: PostgreSQL with TimescaleDB extension
- **Azure Database**: PostgreSQL with TimescaleDB
- **DigitalOcean**: Managed PostgreSQL

Example Timescale Cloud setup:
```python
db = TimescaleDBClient(
    host="your-instance.tsdb.cloud",
    port=5432,
    database="options_db",
    user="tsdbadmin",
    password="your_password"
)
```

---

## 📈 Capacity Planning

Based on options data from Polygon:

| Scenario | Monthly Data | Storage | CPU | RAM |
|----------|--------------|---------|-----|-----|
| 10 tickers, hourly | ~2.6M rows | ~500MB | Low | 2GB |
| 50 tickers, every 15min | ~10M rows | ~1.5GB | Medium | 4GB |
| 500 tickers, tick data | ~100M rows | ~10GB | High | 8GB+ |

With compression enabled, storage is typically **5-10x smaller**.

---

## 📞 Support Resources

- **TimescaleDB Docs**: https://docs.timescale.com/
- **Polygon API Docs**: https://polygon.io/docs/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **GitHub Issues**: File issues in your repo

## ✅ Pre-flight Checklist

Before going to production:
- [ ] Docker/PostgreSQL is running and accessible
- [ ] Schema created and all tables visible
- [ ] Polygon API key is valid and environment variable set
- [ ] Test ingestion runs without errors
- [ ] Data is being inserted into database
- [ ] Queries return results in < 1 second
- [ ] Task Scheduler job created and tested
- [ ] Database backups configured
- [ ] Monitoring/alerts set up
- [ ] Documentation updated for your team
