# TimescaleDB Setup for Options Data

## Installation

### Windows (via Docker - Recommended)
```powershell
# Install Docker Desktop from https://www.docker.com/products/docker-desktop
# Then run:
docker pull timescale/timescaledb:latest-pg15
docker run -d --name timescaledb -p 5432:5432 -e POSTGRES_PASSWORD=password timescale/timescaledb:latest-pg15
```

### Windows (Native PostgreSQL + TimescaleDB)
1. Install PostgreSQL 15+ from https://www.postgresql.org/download/windows/
2. In PostgreSQL 15 directory, add TimescaleDB extension:
```powershell
# Download and install TimescaleDB Windows binary from https://docs.timescale.com/self-hosted/latest/install/windows/
```

## Verify Installation
```powershell
psql -U postgres -h localhost
# Inside psql:
CREATE EXTENSION IF NOT EXISTS timescaledb;
SELECT default_version FROM pg_available_extensions WHERE name = 'timescaledb';
```

## Python Dependencies
```bash
pip install psycopg2-binary sqlalchemy timescale-vector pandas requests
```

## Next Steps
1. Run `schema.sql` to create tables
2. Use `db_client.py` to manage connections
3. Use `polygon_ingestion.py` to stream data from Polygon API
