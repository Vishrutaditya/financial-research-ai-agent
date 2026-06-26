import sqlite3

# Create database
conn = sqlite3.connect("news.db")
cursor = conn.cursor()

# Create watchlist table
cursor.execute("""
CREATE TABLE IF NOT EXISTS watchlist (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_name TEXT NOT NULL,
    stock_symbol TEXT NOT NULL
)
""")

conn.commit()
conn.close()

print("✅ Database and watchlist table created successfully!")