import sqlite3

def init_db():
    # Connect to SQLite database. If the file doesn't exist, it will be created.
    conn = sqlite3.connect('binance_users.db')
    
    # Create a table
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                 buyer_name TEXT NOT NULL UNIQUE,
                 status TEXT,
                 total_fiat_spent_mxn REAL,
                 total_fiat_spent_usd REAL,
                 last_interaction TIMESTAMP)''')

    # Commit changes and close connection
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
