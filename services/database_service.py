"""
services/database_service.py

SQLite Database service for managing saved Indian Stock Watchlists.
Database file is stored locally at database/stocks.db.
"""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

DB_PATH = Path(__file__).resolve().parent.parent / "database" / "stocks.db"


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Creates the watchlist SQLite table if it doesn't already exist."""
    conn = get_connection()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                stock_symbol TEXT NOT NULL UNIQUE,
                company_name TEXT NOT NULL,
                exchange TEXT DEFAULT 'NSE',
                sector TEXT DEFAULT 'N/A',
                added_price REAL,
                target_price REAL,
                notes TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def add_to_watchlist(
    company_name: str,
    stock_symbol: str,
    exchange: str = "NSE",
    sector: str = "N/A",
    added_price: Optional[float] = None,
    notes: str = "",
    target_price: Optional[float] = None,
) -> bool:
    """Adds a stock to the SQLite watchlist. Returns True if inserted, False if already exists."""
    conn = get_connection()
    try:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO watchlist 
            (company_name, stock_symbol, exchange, sector, added_price, target_price, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                company_name,
                stock_symbol.strip().upper(),
                exchange,
                sector or "N/A",
                added_price,
                target_price,
                notes or "",
            ),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def remove_from_watchlist(stock_symbol: str) -> bool:
    """Removes a stock from the watchlist."""
    conn = get_connection()
    try:
        cur = conn.execute(
            "DELETE FROM watchlist WHERE stock_symbol = ?",
            (stock_symbol.strip().upper(),),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_watchlist() -> List[Dict[str, Any]]:
    """Retrieves all items from the watchlist ordered by newest first."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            SELECT id, stock_symbol, company_name, exchange, sector, 
                   added_price, target_price, notes, created_at 
            FROM watchlist 
            ORDER BY id DESC
            """
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def is_in_watchlist(stock_symbol: str) -> bool:
    """Checks if a stock symbol is saved in the watchlist."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT 1 FROM watchlist WHERE stock_symbol = ?",
            (stock_symbol.strip().upper(),),
        )
        return cursor.fetchone() is not None
    finally:
        conn.close()


def update_watchlist_item(
    stock_symbol: str, notes: Optional[str] = None, target_price: Optional[float] = None
) -> None:
    """Updates notes or target price for a watchlist stock."""
    conn = get_connection()
    try:
        if notes is not None:
            conn.execute(
                "UPDATE watchlist SET notes = ? WHERE stock_symbol = ?",
                (notes, stock_symbol.strip().upper()),
            )
        if target_price is not None:
            conn.execute(
                "UPDATE watchlist SET target_price = ? WHERE stock_symbol = ?",
                (target_price, stock_symbol.strip().upper()),
            )
        conn.commit()
    finally:
        conn.close()
