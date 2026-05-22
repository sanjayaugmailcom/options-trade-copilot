"""
Advanced Usage Examples: TimescaleDB Options Analysis
Common queries and analysis patterns for options trading
"""
from db_client import TimescaleDBClient
from datetime import datetime, timedelta
import pandas as pd
from typing import List, Dict


class OptionsAnalyzer:
    """Advanced analysis utilities for options data"""
    
    def __init__(self, db: TimescaleDBClient):
        self.db = db
    
    def get_iv_by_moneyness(self, ticker: str, expiration_date: str) -> pd.DataFrame:
        """
        Get IV grouped by moneyness (how close price is to strike).
        Useful for IV smile analysis.
        """
        query = """
        SELECT 
            strike,
            option_type,
            AVG(iv) as avg_iv,
            MIN(iv) as min_iv,
            MAX(iv) as max_iv,
            COUNT(*) as data_points
        FROM options_quotes
        WHERE ticker = %s AND expiration_date = %s AND iv IS NOT NULL
        GROUP BY strike, option_type
        ORDER BY strike, option_type
        """
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, [ticker, expiration_date])
            cols = [desc[0] for desc in cur.description]
            data = cur.fetchall()
        
        df = pd.DataFrame(data, columns=cols)
        
        # Calculate days to expiration
        exp_date = pd.to_datetime(expiration_date)
        dte = (exp_date - datetime.now()).days
        df['dte'] = dte
        
        return df
    
    def get_option_flow_analysis(
        self,
        ticker: str,
        expiration_date: str,
        last_n_hours: int = 24
    ) -> Dict:
        """
        Analyze options flow: volume, OI changes, IV changes.
        Useful for spotting unusual activity.
        """
        time_cutoff = datetime.now() - timedelta(hours=last_n_hours)
        
        query = """
        SELECT 
            DATE_TRUNC('hour', time) as hour,
            option_type,
            SUM(volume) as total_volume,
            COUNT(DISTINCT strike) as active_strikes,
            AVG(iv) as avg_iv,
            AVG(bid - ask) as avg_spread
        FROM options_quotes
        WHERE ticker = %s 
            AND expiration_date = %s 
            AND time > %s
        GROUP BY hour, option_type
        ORDER BY hour DESC
        """
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, [ticker, expiration_date, time_cutoff])
            cols = [desc[0] for desc in cur.description]
            data = cur.fetchall()
        
        return {
            'periods': len(data),
            'data': [dict(zip(cols, row)) for row in data]
        }
    
    def get_greek_distribution(self, ticker: str, expiration_date: str) -> pd.DataFrame:
        """
        Get latest Greeks distribution across strikes.
        Useful for portfolio hedging analysis.
        """
        query = """
        SELECT DISTINCT ON (strike, option_type)
            strike,
            option_type,
            delta,
            gamma,
            theta,
            vega,
            rho,
            bid,
            ask,
            time
        FROM options_quotes
        WHERE ticker = %s 
            AND expiration_date = %s 
            AND delta IS NOT NULL
        ORDER BY strike, option_type, time DESC
        """
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, [ticker, expiration_date])
            cols = [desc[0] for desc in cur.description]
            data = cur.fetchall()
        
        return pd.DataFrame(data, columns=cols)
    
    def get_put_call_ratio(
        self,
        ticker: str,
        expiration_date: str,
        strike_range: tuple = None
    ) -> Dict:
        """
        Calculate put/call volume and OI ratios.
        Useful for sentiment analysis.
        """
        query = """
        SELECT 
            option_type,
            SUM(volume) as total_volume,
            SUM(open_interest) as total_oi,
            AVG(bid) as avg_bid,
            AVG(iv) as avg_iv
        FROM options_quotes
        WHERE ticker = %s AND expiration_date = %s
        """
        params = [ticker, expiration_date]
        
        if strike_range:
            query += " AND strike BETWEEN %s AND %s"
            params.extend(strike_range)
        
        query += " GROUP BY option_type"
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, params)
            cols = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        
        call_row = None
        put_row = None
        
        for row in rows:
            if row[0] == 'C':
                call_row = dict(zip(cols, row))
            elif row[0] == 'P':
                put_row = dict(zip(cols, row))
        
        if call_row and put_row:
            return {
                'calls': call_row,
                'puts': put_row,
                'put_call_volume_ratio': put_row['total_volume'] / (call_row['total_volume'] or 1),
                'put_call_oi_ratio': put_row['total_oi'] / (call_row['total_oi'] or 1),
            }
        return {}
    
    def get_spread_analysis(self, ticker: str, expiration_date: str) -> pd.DataFrame:
        """
        Analyze bid-ask spreads by strike.
        Useful for understanding liquidity.
        """
        query = """
        SELECT DISTINCT ON (strike, option_type)
            strike,
            option_type,
            bid,
            ask,
            (ask - bid) as spread,
            (ask - bid) / NULLIF((ask + bid) / 2, 0) * 100 as spread_pct,
            volume,
            time
        FROM options_quotes
        WHERE ticker = %s 
            AND expiration_date = %s 
            AND bid IS NOT NULL 
            AND ask IS NOT NULL
        ORDER BY strike, option_type, time DESC
        """
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, [ticker, expiration_date])
            cols = [desc[0] for desc in cur.description]
            data = cur.fetchall()
        
        df = pd.DataFrame(data, columns=cols)
        return df.sort_values('spread_pct', ascending=False)
    
    def get_iv_term_structure(self, ticker: str) -> pd.DataFrame:
        """
        Get IV term structure (IV by expiration date).
        Useful for understanding volatility curve.
        """
        query = """
        SELECT 
            expiration_date,
            COUNT(DISTINCT strike) as strikes_available,
            AVG(iv) as avg_iv,
            MIN(iv) as min_iv,
            MAX(iv) as max_iv,
            EXTRACT(DAY FROM expiration_date - NOW()) as dte
        FROM options_quotes
        WHERE ticker = %s AND iv IS NOT NULL
        GROUP BY expiration_date
        ORDER BY expiration_date
        """
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, [ticker])
            cols = [desc[0] for desc in cur.description]
            data = cur.fetchall()
        
        return pd.DataFrame(data, columns=cols)
    
    def export_for_ml(
        self,
        ticker: str,
        expiration_date: str,
        output_csv: str = None
    ) -> pd.DataFrame:
        """
        Export options data in format suitable for ML/analysis.
        Includes Greeks, technicals, and normalized features.
        """
        query = """
        SELECT DISTINCT ON (strike, option_type, DATE_TRUNC('hour', time))
            time,
            strike,
            option_type,
            (ask + bid) / 2 as mid_price,
            (ask - bid) / NULLIF((ask + bid) / 2, 0) as spread_pct,
            volume,
            open_interest,
            delta,
            gamma,
            theta,
            vega,
            rho,
            iv,
            EXTRACT(DAY FROM %s::date - NOW()::date) as days_to_exp
        FROM options_quotes
        WHERE ticker = %s AND expiration_date = %s
        ORDER BY strike, option_type, DATE_TRUNC('hour', time)
        """
        
        with self.db.get_connection() as conn:
            cur = conn.cursor()
            cur.execute(query, [expiration_date, ticker, expiration_date])
            cols = [desc[0] for desc in cur.description]
            data = cur.fetchall()
        
        df = pd.DataFrame(data, columns=cols)
        
        # Normalize Greeks to 0-1 range
        greek_cols = ['delta', 'gamma', 'theta', 'vega', 'rho']
        for col in greek_cols:
            if col in df.columns:
                df[f'{col}_norm'] = (df[col] - df[col].min()) / (df[col].max() - df[col].min())
        
        # Export if requested
        if output_csv:
            df.to_csv(output_csv, index=False)
            print(f"✓ Exported {len(df)} rows to {output_csv}")
        
        return df


# Example usage
if __name__ == "__main__":
    db = TimescaleDBClient()
    analyzer = OptionsAnalyzer(db)
    
    ticker = "AAPL"
    exp_date = "2026-06-18"
    
    print("=" * 60)
    print(f"Advanced Analysis for {ticker} {exp_date}")
    print("=" * 60)
    
    # IV Analysis
    print("\n📊 IV by Moneyness:")
    iv_df = analyzer.get_iv_by_moneyness(ticker, exp_date)
    print(iv_df.head(10).to_string())
    
    # Greeks Distribution
    print("\n📈 Greeks Distribution:")
    greeks_df = analyzer.get_greek_distribution(ticker, exp_date)
    print(greeks_df[['strike', 'option_type', 'delta', 'gamma', 'theta']].head().to_string())
    
    # Put/Call Analysis
    print("\n⚖️ Put/Call Analysis:")
    pc_ratio = analyzer.get_put_call_ratio(ticker, exp_date)
    if pc_ratio:
        print(f"Put/Call Volume Ratio: {pc_ratio['put_call_volume_ratio']:.2f}")
        print(f"Put/Call OI Ratio: {pc_ratio['put_call_oi_ratio']:.2f}")
    
    # Spread Analysis (liquidity)
    print("\n💰 Least Liquid Options (largest spreads):")
    spread_df = analyzer.get_spread_analysis(ticker, exp_date)
    print(spread_df[['strike', 'option_type', 'spread_pct', 'volume']].head().to_string())
    
    # Term Structure
    print("\n📅 IV Term Structure:")
    term_df = analyzer.get_iv_term_structure(ticker)
    print(term_df[['expiration_date', 'avg_iv', 'dte']].head().to_string())
    
    # Export for ML
    print("\n🤖 Exporting for ML analysis...")
    ml_df = analyzer.export_for_ml(ticker, exp_date, f"{ticker}_options_ml.csv")
    print(f"Exported {len(ml_df)} records with {len(ml_df.columns)} features")
    
    db.close()
