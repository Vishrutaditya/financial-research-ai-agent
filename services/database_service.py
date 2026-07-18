"""
services/database_service.py

Watchlist persistence. All DB access is scoped inside functions -- nothing
runs at import time -- and the path is resolved relative to this file so
it works no matter what directory Streamlit is launched from.
"""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "news.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_db() -> None:
    """Creates the watchlist table if it doesn't already exist. Safe to call repeatedly."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT NOT NULL,
                stock_symbol TEXT NOT NULL,
                UNIQUE(stock_symbol)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def add_to_watchlist(company_name: str, stock_symbol: str) -> None:
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist (company_name, stock_symbol) VALUES (?, ?)",
            (company_name, stock_symbol),
        )
        conn.commit()
    finally:
        conn.close()


def remove_from_watchlist(stock_symbol: str) -> None:
    conn = get_connection()
    try:
        conn.execute("DELETE FROM watchlist WHERE stock_symbol = ?", (stock_symbol,))
        conn.commit()
    finally:
        conn.close()


def get_watchlist() -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.execute(
            "SELECT id, company_name, stock_symbol FROM watchlist ORDER BY id DESC"
        )
        rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {"id": row[0], "company_name": row[1], "stock_symbol": row[2]}
        for row in rows
    ]