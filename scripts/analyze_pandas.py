import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join("results", "metrics.db")

def analyze():
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    
    try:
        # Load data into DataFrame
        df = pd.read_sql_query("SELECT * FROM execution_metrics", conn)
        
        if df.empty:
            print("No data found in database.")
            return

        # Group by run_id and scenario_name
        # Calculate average latency and count success/failures
        summary = df.groupby(['run_id', 'scenario_name']).agg(
            total_requests=('id', 'count'),
            device_count=('device_id', 'nunique'),
            avg_latency_ms=('latency_ms', 'mean'),
            success_count=('status', lambda x: (x == 'SUCCESS').sum())
        ).reset_index()

        # Calculate success rate
        summary['success_rate_pct'] = (summary['success_count'] / summary['total_requests']) * 100
        
        print("\n--- Analysis Report ---")
        print(summary.to_string(index=False))
        print("\n-----------------------")

    except Exception as e:
        print(f"Error analyzing metrics: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    analyze()

