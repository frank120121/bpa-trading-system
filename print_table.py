import sqlite3
import asyncio

async def fetch_data(conn, query, params=None):
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    rows = cursor.fetchall()
    return rows

async def print_all_tables(database_path):
    conn = sqlite3.connect(database_path)
    
    # Getting the list of tables in the database
    tables = await fetch_data(conn, "SELECT name FROM sqlite_master WHERE type='table';")
    table_names = [table[0] for table in tables]
    
    for table_name in table_names:
        print(f"\nContents of {table_name}:\n{'='*30}")
        
        # Fetching columns for the table
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [desc[1] for desc in cursor.fetchall()]
        
        # Fetching rows from the table
        rows = await fetch_data(conn, f"SELECT * FROM {table_name}")
        
        # Printing the header
        header = " | ".join(columns)
        print(header)
        print("-"*len(header))
        
        # Printing rows
        for row in rows:
            print(" | ".join(map(str, row)))

    conn.close()

async def main():
    database_path = "crypto_bot.db"
    await print_all_tables(database_path)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())

