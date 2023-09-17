import logging
from logging_config import setup_logging
import aiosqlite
import asyncio
import json
setup_logging()
logger = logging.getLogger(__name__)
async def create_connection(db_file, num_retries=3, delay_seconds=5):
    logger.info("Inside async_create_connection function")
    conn = None
    retries = 0
    while retries < num_retries:
        try:
            conn = await aiosqlite.connect(db_file)
            return conn
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}. Retrying in {delay_seconds} seconds.")
            await asyncio.sleep(delay_seconds)
            retries += 1
    logger.error("Max retries reached. Could not establish the database connection.")
    return None
def handle_error(e, message_prefix):
    if isinstance(e, Exception):
        logger.error(f"Database error: {e}")
    else:
        logger.error(f"{message_prefix}: {e}")
async def execute_and_commit(conn, sql, params=None):
    try:
        cursor = await conn.execute(sql, params)
        await conn.commit()
        await cursor.close()
    except Exception as e:
        handle_error(e, "Exception in execute_and_commit")
async def update_order_status(conn, order_no, order_status):
    sql = "UPDATE orders SET order_status = ? WHERE order_no = ?"
    params = (order_status, order_no)
    await execute_and_commit(conn, sql, params)
async def reset_reply_count(conn, order_no):
    sql = "UPDATE orders SET reply_count = 0 WHERE order_no = ?"
    params = (order_no,)
    await execute_and_commit(conn, sql, params)
async def update_status_from_system_type(conn, msg_json, order_no):
    
    try:
        content = msg_json.get('content', '')
        content_dict = json.loads(content)
        system_type = content_dict.get('type', '')
        print(system_type)
    except json.JSONDecodeError:
        system_type = ''
    status_map = {
        'buyer_merchant_trading': 3,
        'seller_merchant_trading': 1,
        'seller_payed': 2,
        'buyer_payed': 8,
        'submit_appeal': 9,
        'be_appeal': 5,
        'seller_completed': 4,
        'seller_cancelled': 6,
        'cancelled_by_system': 7
    }
    status = status_map.get(system_type, None)
    if status is not None:
        if order_no:
            sql = "UPDATE orders SET order_status = ? WHERE order_no = ?"
            params = (status, order_no)
            await execute_and_commit(conn, sql, params)
async def update_reply_count(conn, order_no):
    sql = "UPDATE orders SET reply_count = reply_count + 1 WHERE order_no = ?"
    params = (order_no,)
    await execute_and_commit(conn, sql, params)
async def update_total_fiat_spent(conn, buyer_id, total_price):
    sql = '''UPDATE users SET total_crypto_sold_30d = total_crypto_sold_30d + ? WHERE id = ?'''
    await execute_and_commit(conn, sql, (total_price, buyer_id))
async def get_order_details(conn, order_no):
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT * FROM orders WHERE order_no=?", (order_no,))
            row = await cursor.fetchone()
            if row:
                column_names = [desc[0] for desc in cursor.description]
                return {column_names[i]: row[i] for i in range(len(row))}
            else:
                return None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None
async def get_reply_count(conn, order_no):
    try:
        async with conn.cursor() as cursor:
            await cursor.execute("SELECT reply_count FROM orders WHERE order_no = ?", (order_no,))
            row = await cursor.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return None
async def create_table(conn, create_table_sql):
    async with conn.cursor() as cursor:
        await cursor.execute(create_table_sql)
async def order_exists(conn, order_no):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT id FROM orders WHERE order_no = ?", (order_no,))
        row = await cursor.fetchone()
        return bool(row)
async def find_or_insert_merchant(conn, sellerName):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT id FROM merchants WHERE sellerName = ?", (sellerName,))
        row = await cursor.fetchone()
        if row:
            return row[0]
        else:
            await cursor.execute("INSERT INTO merchants (sellerName) VALUES (?, ?, ?)", (sellerName))
            return cursor.lastrowid
async def find_or_insert_buyer(conn, buyer_name, merchant_id):
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT id FROM users WHERE name = ? AND merchant_id = ?", (buyer_name, merchant_id))
        row = await cursor.fetchone()
        if row:
            return row[0]
        else:
            await cursor.execute("INSERT INTO users (name, merchant_id, kyc_status, total_crypto_sold_30d, total_crypto_sold_lifetime) VALUES (?, ?, 0, 0.0, 0.0)", (buyer_name, merchant_id))
            return cursor.lastrowid
async def insert_order(conn, order_tuple):
    async with conn.cursor() as cursor:
        await cursor.execute('''INSERT INTO orders(order_no, buyer_name, seller_name, trade_type, order_status, total_price, fiat_unit, bot_replied)
                                VALUES(?,?,?,?,?,?,?,?)''', order_tuple)
        return cursor.lastrowid
async def insert_or_update_order(conn, order_details):
    try:
        logger.debug(f"Order Details Received in db:")
        seller_name = order_details['data']['sellerName']
        buyer_name = order_details['data']['buyerName']
        order_no = order_details['data']['orderNumber']
        trade_type = order_details['data']['tradeType']
        order_status = order_details['data']['orderStatus']
        total_price = order_details['data']['totalPrice']
        fiat_unit = order_details['data']['fiatUnit']
        logger.debug(f"Seller Name: {seller_name}, Buyer Name: {buyer_name}, Order Status: {order_status}")
        if None in (seller_name, buyer_name, order_no, trade_type, order_status, total_price, fiat_unit):
            logger.error("One or more required fields are None. Aborting operation.")
            return
        if await order_exists(conn, order_no):
            sql = """
                UPDATE orders
                SET seller_name = ?,
                    buyer_name = ?,
                    trade_type = ?,
                    order_status = ?,
                    total_price = ?,
                    fiat_unit = ?
                WHERE order_no = ?
            """
            params = (seller_name, buyer_name, trade_type, order_status, total_price, fiat_unit, order_no)
            await execute_and_commit(conn, sql, params)
        else:
            merchant_id = await find_or_insert_merchant(conn, seller_name)
            buyer_id = await find_or_insert_buyer(conn, buyer_name, merchant_id)
            await insert_order(conn, (order_no, buyer_name, seller_name, trade_type, order_status, total_price, fiat_unit, False))
            await update_total_fiat_spent(conn, buyer_id, float(total_price))
    except Exception as e:
        logger.error(f"Error in insert_or_update_order: {e}")
async def column_exists(conn, table_name, column_name):
    async with conn.cursor() as cursor:
        await cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [column[1] for column in await cursor.fetchall()]
        return column_name in columns
async def add_reply_count_column(conn):
    async with conn.cursor() as cursor:
        await cursor.execute("ALTER TABLE orders ADD COLUMN reply_count INTEGER DEFAULT 0;")
    await conn.commit()
async def is_column_exists(conn, table_name, column_name):
    sql_check_column = f"PRAGMA table_info({table_name});"
    cursor = await conn.execute(sql_check_column)
    rows = await cursor.fetchall()
    return any(row[1] == column_name for row in rows)
async def alter_orders_table_add_payment_proof(conn):
    sql_alter_orders_table = """ALTER TABLE orders
                                ADD COLUMN payment_proof BLOB;"""
    await execute_and_commit(conn, sql_alter_orders_table)
async def add_image_to_order(conn, order_no, image_data):
    sql_update_order_with_image = """
    UPDATE orders
    SET payment_proof = ?
    WHERE order_no = ?;
    """
    await execute_and_commit(conn, sql_update_order_with_image, (image_data, order_no))
async def order_has_image(conn, order_no):
    sql_check_for_image = """
    SELECT payment_proof FROM orders WHERE order_no = ?;
    """
    try:
        async with conn.cursor() as cur:
            await cur.execute(sql_check_for_image, (order_no,))
            row = await cur.fetchone()
        return row[0] is not None if row else False
    except Exception as e:
        logger.error(f"Error in order_has_image: {e}")
        return False
async def main():
    database = "crypto_bot.db"
    sql_create_merchants_table = """CREATE TABLE IF NOT EXISTS merchants (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                sellerName TEXT NOT NULL UNIQUE
                                );"""
    sql_create_users_table = """CREATE TABLE IF NOT EXISTS users (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                name TEXT NOT NULL,
                                merchant_id INTEGER NOT NULL,
                                kyc_status INTEGER,
                                total_crypto_sold_30d REAL,
                                total_crypto_sold_lifetime REAL,
                                FOREIGN KEY (merchant_id) REFERENCES merchants (id)
                                );"""
    sql_create_orders_table = """CREATE TABLE IF NOT EXISTS orders (
                              id INTEGER PRIMARY KEY AUTOINCREMENT,
                              order_no TEXT NOT NULL UNIQUE,
                              buyer_name TEXT,
                              seller_name TEXT,
                              trade_type TEXT,
                              order_status INTEGER,
                              total_price REAL,
                              fiat_unit TEXT,
                              bot_replied BOOLEAN,
                              reply_count INTEGER DEFAULT 0
                              );"""
    sql_create_exchange_accounts_table = """CREATE TABLE IF NOT EXISTS exchange_accounts (
                                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                                            merchant_id INTEGER NOT NULL,
                                            exchange_name TEXT NOT NULL,
                                            FOREIGN KEY (merchant_id) REFERENCES merchants (id)
                                            );"""
    sql_create_bank_accounts_table = """CREATE TABLE IF NOT EXISTS bank_accounts (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        merchant_id INTEGER NOT NULL,
                                        bank_name TEXT NOT NULL,
                                        FOREIGN KEY (merchant_id) REFERENCES merchants (id)
                                        );"""
    sql_create_account_balances_table = """CREATE TABLE IF NOT EXISTS account_balances (
                                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                                           account_type TEXT NOT NULL,  -- 'exchange' or 'bank'
                                           account_id INTEGER NOT NULL,
                                           asset_type TEXT NOT NULL,
                                           balance REAL NOT NULL
                                           );"""
    conn = await create_connection(database)
    if conn is not None:
        await create_table(conn, sql_create_merchants_table)
        await create_table(conn, sql_create_users_table)
        await create_table(conn, sql_create_orders_table)
        await create_table(conn, sql_create_exchange_accounts_table)
        await create_table(conn, sql_create_bank_accounts_table)
        await create_table(conn, sql_create_account_balances_table)
        column_exists = await is_column_exists(conn, 'orders', 'payment_proof')
        if not column_exists:
            await alter_orders_table_add_payment_proof(conn)
        await conn.close()
    else:
        logger.error("Error! Cannot create the database connection.")
if __name__ == '__main__':
    asyncio.run(main())