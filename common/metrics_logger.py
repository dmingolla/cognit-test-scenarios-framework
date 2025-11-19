"""
Simple metrics logger to store metrics in a SQLite database.
"""

import sqlite3
import threading
import os
from datetime import datetime

class MetricsLogger:
    _instance = None
    _lock = threading.Lock()
    _initialized = False
    
    def __new__(cls, db_path="results/metrics.db"):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(MetricsLogger, cls).__new__(cls)
                    cls._instance.db_path = db_path
        return cls._instance
    
    def _ensure_db_initialized(self):
        if self._initialized:
            return

        with self._lock:
            if self._initialized:
                return
                
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            # Create table if it doesn't exist
            # We use a separate connection here
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS execution_metrics (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        run_id TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        scenario_name TEXT NOT NULL,
                        device_id TEXT NOT NULL,
                        task_name TEXT NOT NULL,
                        app_reqs_json TEXT,
                        status TEXT NOT NULL,
                        latency_ms INTEGER NOT NULL,
                        metric_value REAL,
                        error_msg TEXT
                    )
                """)
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_scenario_timestamp 
                    ON execution_metrics(scenario_name, timestamp)
                """)
                conn.commit()
                self._initialized = True
            finally:
                conn.close()

    def _execute_query(self, query, params=()):
        # SQLite connections cannot be shared across threads/greenlets safely in all cases
        # Opening a new connection per operation is safer for concurrency here
        with self._lock:
            conn = sqlite3.connect(self.db_path)
            try:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
            finally:
                conn.close()

    def log_metric(self, run_id, scenario_name, device_id, task_name, status, latency_ms, app_reqs_json=None, metric_value=None, error_msg=None):
        # Ensure DB is ready before writing
        self._ensure_db_initialized()
        
        timestamp = datetime.now().isoformat()
        query = """
            INSERT INTO execution_metrics 
            (run_id, timestamp, scenario_name, device_id, task_name, app_reqs_json, status, latency_ms, metric_value, error_msg)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        self._execute_query(query, (
            run_id, timestamp, scenario_name, device_id, task_name, app_reqs_json, status, 
            latency_ms, metric_value, error_msg
        ))
