-- TimescaleDB Schema for Options Data
-- Connect to your database: psql -U postgres -h localhost -d options_db

-- Create database
CREATE DATABASE options_db;
\c options_db;

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Options Quotes Table (main time-series data)
-- Stores real-time/intraday option quotes
CREATE TABLE options_quotes (
    time TIMESTAMPTZ NOT NULL,
    ticker TEXT NOT NULL,
    option_symbol TEXT NOT NULL,
    strike DECIMAL(10, 2) NOT NULL,
    expiration_date DATE NOT NULL,
    option_type CHAR(1) NOT NULL, -- 'C' or 'P'
    
    -- Price data
    bid DECIMAL(10, 4),
    ask DECIMAL(10, 4),
    last DECIMAL(10, 4),
    
    -- Volume & OI
    volume BIGINT,
    open_interest BIGINT,
    
    -- Greeks (optional but useful)
    delta DECIMAL(8, 6),
    gamma DECIMAL(8, 6),
    theta DECIMAL(8, 6),
    vega DECIMAL(8, 6),
    rho DECIMAL(8, 6),
    iv DECIMAL(8, 6), -- Implied Volatility
    
    -- Metadata
    source TEXT DEFAULT 'polygon',
    polygon_request_id TEXT
);

-- Convert to hypertable (partitioned by time)
SELECT create_hypertable('options_quotes', 'time', if_not_exists => TRUE);

-- Create indexes for common queries
CREATE INDEX idx_options_quotes_ticker_time ON options_quotes (ticker, time DESC);
CREATE INDEX idx_options_quotes_symbol_time ON options_quotes (option_symbol, time DESC);
CREATE INDEX idx_options_quotes_strike_exp ON options_quotes (strike, expiration_date);
CREATE INDEX idx_options_quotes_type ON options_quotes (option_type);

-- Options Chain Table (reference data - updates less frequently)
-- Stores option contract details
CREATE TABLE options_chains (
    contract_id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    option_symbol TEXT NOT NULL,
    strike DECIMAL(10, 2) NOT NULL,
    expiration_date DATE NOT NULL,
    option_type CHAR(1) NOT NULL,
    
    -- Static data
    shares_per_contract INT DEFAULT 100,
    underlying_price DECIMAL(10, 2),
    last_updated TIMESTAMPTZ DEFAULT NOW(),
    
    -- Polygon specific
    polygon_contract_id TEXT UNIQUE
);

-- Index for fast lookups
CREATE INDEX idx_chains_ticker_exp ON options_chains (ticker, expiration_date);
CREATE INDEX idx_chains_symbol ON options_chains (option_symbol);

-- Daily Summary Table (for faster aggregations)
CREATE TABLE options_daily_summary (
    date DATE NOT NULL,
    ticker TEXT NOT NULL,
    strike DECIMAL(10, 2) NOT NULL,
    expiration_date DATE NOT NULL,
    option_type CHAR(1) NOT NULL,
    
    open_price DECIMAL(10, 4),
    high_price DECIMAL(10, 4),
    low_price DECIMAL(10, 4),
    close_price DECIMAL(10, 4),
    avg_volume BIGINT,
    total_volume BIGINT
);

-- Convert to hypertable
SELECT create_hypertable('options_daily_summary', 'date', if_not_exists => TRUE);
CREATE INDEX idx_daily_summary_ticker ON options_daily_summary (ticker, date DESC);

-- Retention policy (keep 2 years of detailed data, longer for summaries)
SELECT add_retention_policy('options_quotes', INTERVAL '2 years', if_not_exists => TRUE);
SELECT add_retention_policy('options_daily_summary', INTERVAL '5 years', if_not_exists => TRUE);

-- Compression (keep last 7 days uncompressed for faster writes)
ALTER TABLE options_quotes SET (
    timescaledb.compress,
    timescaledb.compress_orderby = 'time DESC, ticker'
);

SELECT add_compression_policy('options_quotes', INTERVAL '7 days', if_not_exists => TRUE);
