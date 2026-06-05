"""
Initialize the options_db schema.
Creates the options_quotes hypertable, unique constraint, and indexes.
Safe to re-run — uses IF NOT EXISTS throughout.

Run: python init_db.py
"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DDL = """
-- Main table
CREATE TABLE IF NOT EXISTS options_quotes (
    time                TIMESTAMPTZ      NOT NULL,
    ticker              TEXT             NOT NULL,
    option_symbol       TEXT             NOT NULL,
    strike              DOUBLE PRECISION,
    expiration_date     DATE,
    option_type         CHAR(1),
    bid                 DOUBLE PRECISION,
    ask                 DOUBLE PRECISION,
    last                DOUBLE PRECISION,
    volume              BIGINT,
    open_interest       BIGINT,
    delta               DOUBLE PRECISION,
    gamma               DOUBLE PRECISION,
    theta               DOUBLE PRECISION,
    vega                DOUBLE PRECISION,
    rho                 DOUBLE PRECISION,
    iv                  DOUBLE PRECISION,
    source              TEXT,
    polygon_request_id  TEXT
);

-- TimescaleDB hypertable
SELECT create_hypertable(
    'options_quotes', 'time',
    if_not_exists => TRUE,
    migrate_data   => TRUE
);

-- Unique constraint for deduplication
ALTER TABLE options_quotes
    DROP CONSTRAINT IF EXISTS uq_options_quotes_symbol_time;

ALTER TABLE options_quotes
    ADD CONSTRAINT uq_options_quotes_symbol_time
    UNIQUE (option_symbol, time);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_oq_ticker_expiry_time
    ON options_quotes (ticker, expiration_date, time DESC);

CREATE INDEX IF NOT EXISTS idx_oq_ticker_time
    ON options_quotes (ticker, time DESC);

CREATE INDEX IF NOT EXISTS idx_oq_expiry
    ON options_quotes (expiration_date);

CREATE INDEX IF NOT EXISTS idx_oq_source
    ON options_quotes (source);
"""


def main():
    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", 5432)),
        dbname=os.getenv("DB_NAME", "options_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", "password"),
    )
    conn.autocommit = False
    cur = conn.cursor()

    print("Creating options_quotes table and hypertable…")
    try:
        # Execute each statement separately so errors are clear
        for stmt in [s.strip() for s in DDL.split(";") if s.strip()]:
            cur.execute(stmt)
            print(f"  OK: {stmt[:72].replace(chr(10), ' ')}")

        conn.commit()
        print("\nOK: Schema ready.")

        # Show what was created
        cur.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'options_quotes'
            ORDER BY indexname
        """)
        rows = cur.fetchall()
        print(f"\n{len(rows)} index(es) on options_quotes:")
        for name, defn in rows:
            print(f"  {name}")

        cur.execute("""
            SELECT conname, contype, pg_get_constraintdef(oid)
            FROM pg_constraint
            WHERE conrelid = 'options_quotes'::regclass
        """)
        constraints = cur.fetchall()
        print(f"\n{len(constraints)} constraint(s):")
        for name, typ, defn in constraints:
            print(f"  [{typ}] {name}: {defn}")

    except Exception as e:
        conn.rollback()
        print(f"\nERROR: {e}")
        raise
    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
