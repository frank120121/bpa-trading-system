import sqlite3
import logging
from logging_config import setup_logging
setup_logging(log_filename='Binance_c2c_logger.log')
logger = logging.getLogger(__name__)

DATABASE_PATH = 'C:/Users/p7016/Documents/bpa/asset_balances.db'

def setup_db():
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS balances (
            id INTEGER PRIMARY KEY,
            exchange_id INTEGER,
            account TEXT,
            asset TEXT,
            balance FLOAT,
            UNIQUE(exchange_id, account, asset)
        )
    ''')
    connection.commit()
    connection.close()

def update_balance(exchange_id, account, combined_balances):
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    
    for asset, balance in combined_balances.items():
        logging.info(f"Updating {account} - {asset}: {balance}")
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO balances (exchange_id, account, asset, balance)
                VALUES (?, ?, ?, ?)
            ''', (exchange_id, account, asset, balance))
            logging.info(f"Successfully updated {account} - {asset}: {balance}")
        except sqlite3.Error as e:
            logging.error(f"Failed to update {account} - {asset}: {balance}, Error: {str(e)}")
        
    connection.commit()
    connection.close()

def get_balance(exchange_id, account):
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('''
            SELECT asset, balance 
            FROM balances 
            WHERE exchange_id = ? AND account = ?
        ''', (exchange_id, account))
        balances = {asset: balance for asset, balance in cursor.fetchall()}
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return {}
    finally:
        if connection:
            connection.close()
    return balances
def get_all_balances():
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('''
            SELECT exchange_id, account, asset, balance 
            FROM balances
        ''')
        balances_data = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if connection:
            connection.close()
    return balances_data

def print_all_balances():
    balances_data = get_all_balances()
    
    if balances_data:
        for exchange_id, account, asset, balance in balances_data:
            print(f"Exchange ID: {exchange_id}, Account: {account}, Asset: {asset}, Balance: {balance}")
    else:
        print("No balance data found.")
def get_total_asset_balances():
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('''
            SELECT asset, SUM(balance)
            FROM balances
            GROUP BY asset
        ''')
        total_balances = cursor.fetchall()
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []
    finally:
        if connection:
            connection.close()
    return total_balances

def print_total_asset_balances():
    total_balances = get_total_asset_balances()
    
    if total_balances:
        for asset, total_balance in total_balances:
            print(f"Asset: {asset}, Total Balance: {total_balance}")
    else:
        print("No balance data found.")

if __name__ == "__main__":
    setup_db()
    #print_all_balances()
    print_total_asset_balances()