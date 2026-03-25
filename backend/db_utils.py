# backend/db_utils.py
"""
Centralized SQLite connection utility.
Uses WAL mode + check_same_thread=False for concurrent FastAPI access.
"""

import sqlite3
import threading

_local = threading.local()


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Get a new SQLite connection with WAL mode enabled.
    WAL mode prevents 'database is locked' errors under concurrent load.
    Since connections are cheap, we don't cache them to avoid 'closed db' errors.
    """
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
    # Enable Write-Ahead Logging for concurrency
    conn.execute("PRAGMA journal_mode=WAL;")
    # Set busy timeout to 5000ms (5 seconds)
    conn.execute("PRAGMA busy_timeout=5000;")
    # Optional performance pragmas
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA cache_size=-2000;")
    
    conn.row_factory = sqlite3.Row
    return conn
