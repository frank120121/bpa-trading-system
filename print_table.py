import sqlite3
import asyncio

async def fetch_data(conn, query):
    cursor = conn.cursor()
    cursor.execute(query)
    rows = cursor.fetchall()
    return rows

async def print_all_orders(database_path):
    conn = sqlite3.connect(database_path)
    
    query = "SELECT * FROM orders"
    rows = await fetch_data(conn, query)
    
    print(f"{'ID':<5} {'Order No':<10} {'Buyer Name':<15} {'Seller Name':<15} {'Trade Type':<10} {'Order Status':<15} {'Total Price':<12} {'Fiat Unit':<10} {'Bot Replied':<12} {'Reply Count':<12}")
    
    for row in rows:
        print(f"{row[0]:<5} {row[1]:<10} {row[2]:<15} {row[3]:<15} {row[4]:<10} {row[5]:<15} {row[6]:<12} {row[7]:<10} {row[8]:<12} {row[9]:<12}")

    conn.close()

# You can run the function like this:
loop = asyncio.get_event_loop()
loop.run_until_complete(print_all_orders("crypto_bot.db"))
