import time
import sqlite3
from sqlite3 import Error
import logging

logging.basicConfig(filename='database.log', level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s')


def create_connection(db_file, num_retries=3, delay_seconds=5):
    conn = None
    retries = 0

    while retries < num_retries:
        try:
            conn = sqlite3.connect(db_file)
            logging.info(f"Successfully connected to database: {db_file}")
            return conn
        except Error as e:
            logging.error(f"Failed to connect to database: {e}. Retrying in {delay_seconds} seconds.")
            time.sleep(delay_seconds)
            retries += 1

    logging.error("Max retries reached. Could not establish the database connection.")
    return None


def handle_error(e, message_prefix):
    if isinstance(e, sqlite3.Error):
        logging.error(f"Database error: {e}")
    else:
        logging.error(f"{message_prefix}: {e}")


def execute_and_commit(conn, sql, params):
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
    except Exception as e:
        handle_error(e, "Exception in execute_and_commit")

def update_order_status(conn, order_no, order_status):
    sql = "UPDATE orders SET order_status = ? WHERE order_no = ?"
    params = (order_status, order_no)
    execute_and_commit(conn, sql, params)

def reset_reply_count(conn, order_no):
    sql = "UPDATE orders SET reply_count = 0 WHERE order_no = ?"
    params = (order_no,)
    execute_and_commit(conn, sql, params)

def update_status_from_system_type(conn, order_no, system_type):
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
        try:
            cur = conn.cursor()
            cur.execute("UPDATE orders SET order_status = ? WHERE order_no = ?", (status, order_no))
            conn.commit()
            print(f"Order {order_no} status updated to {status}.")
        except Exception as e:
            print(f"An error occurred while updating the order status: {e}")
    else:
        print(f"Unrecognized system_type '{system_type}' for order {order_no}. No update performed.")

def update_reply_count(conn, order_no):
    sql = "UPDATE orders SET reply_count = reply_count + 1 WHERE order_no = ?"
    params = (order_no,)
    execute_and_commit(conn, sql, params)

def update_total_fiat_spent(conn, buyer_id, total_price):
    sql = '''UPDATE users SET total_crypto_sold_30d = total_crypto_sold_30d + ? WHERE id = ?'''
    cur = conn.cursor()
    cur.execute(sql, (total_price, buyer_id))

def get_order_details(conn, order_no):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM orders WHERE order_no=?", (order_no,))
    row = cursor.fetchone()

    if row:
        column_names = [desc[0] for desc in cursor.description]
        order_details_dict = {column_names[i]: row[i] for i in range(len(row))}
        return order_details_dict
    else:
        return None
import sqlite3

def get_reply_count(conn, order_no):

    cur = conn.cursor()
    cur.execute("SELECT reply_count FROM orders WHERE order_no = ?", (order_no,))
    row = cur.fetchone()
    
    if row is not None:
        return row[0]
    else:
        print(f"Order {order_no} not found in database.")
        return None


def create_table(conn, create_table_sql):
    try:
        c = conn.cursor()
        c.execute(create_table_sql)
    except Error as e:
        print(e)

def print_table(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    print(f"--- {table_name} ---")
    for row in rows:
        print(row)
    print("\n")

def order_exists(conn, order_no):
    cur = conn.cursor()
    cur.execute("SELECT id FROM orders WHERE order_no = ?", (order_no,))
    row = cur.fetchone()
    return bool(row)

def find_or_insert_merchant(conn, sellerName, nickname, name):
    cur = conn.cursor()
    cur.execute("SELECT id FROM merchants WHERE sellerName = ?", (sellerName,))
    row = cur.fetchone()

    if row:
        return row[0]
    else:
        cur.execute("INSERT INTO merchants (nickname, name, sellerName) VALUES (?, ?, ?)", (nickname, name, sellerName))
        return cur.lastrowid

def find_or_insert_buyer(conn, buyer_name, merchant_id):
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE name = ? AND merchant_id = ?", (buyer_name, merchant_id))
    row = cur.fetchone()

    if row:
        return row[0]
    else:
        cur.execute("INSERT INTO users (name, merchant_id, kyc_status, total_crypto_sold_30d, total_crypto_sold_lifetime) VALUES (?, ?, 0, 0.0, 0.0)", (buyer_name, merchant_id))
        return cur.lastrowid

def insert_order(conn, order_tuple):
    sql = '''INSERT INTO orders(order_no, buyer_name, seller_name, trade_type, order_status, total_price, fiat_unit, bot_replied)
             VALUES(?,?,?,?,?,?,?,?)'''
    cur = conn.cursor()
    cur.execute(sql, order_tuple)
    return cur.lastrowid

def insert_or_update_order(conn, order_details):
    seller_name = order_details['sellerName']
    buyer_name = order_details['buyerName']
    order_no = order_details['orderNumber']
    trade_type = order_details['tradeType']
    order_status = order_details['orderStatus']
    total_price = order_details['totalPrice']
    fiat_unit = order_details['fiatUnit']

    if not order_exists(conn, order_no):
        merchant_id = find_or_insert_merchant(conn, seller_name, "MFMP", "MUNOZ PEREA MARIA FERNANDA")
        buyer_id = find_or_insert_buyer(conn, buyer_name, merchant_id)
        insert_order(conn, (order_no, buyer_name, seller_name, trade_type, order_status, total_price, fiat_unit, False))
        update_total_fiat_spent(conn, buyer_id, float(total_price))

def column_exists(conn, table_name, column_name):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table_name})")
    columns = [column[1] for column in cur.fetchall()]
    return column_name in columns

def add_reply_count_column(conn):
    cur = conn.cursor()
    cur.execute("ALTER TABLE orders ADD COLUMN reply_count INTEGER DEFAULT 0;")
    conn.commit()



def main():
    logging.info("Starting main function.")

    database = "crypto_bot.db"

    sql_create_merchants_table = """CREATE TABLE IF NOT EXISTS merchants (
                                id INTEGER PRIMARY KEY AUTOINCREMENT,
                                nickname TEXT NOT NULL,
                                name TEXT NOT NULL,
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

    conn = create_connection(database)

    if conn is not None:
        logging.info("Creating merchants table.")
        create_table(conn, sql_create_merchants_table)

        logging.info("Creating users table.")
        create_table(conn, sql_create_users_table)

        logging.info("Creating orders table.")
        create_table(conn, sql_create_orders_table)

        if not column_exists(conn, 'orders', 'reply_count'):
            logging.info("Adding reply_count column to orders table.")
            add_reply_count_column(conn)

    else:
        logging.error("Error! Cannot create the database connection.")


if __name__ == '__main__':
    main()