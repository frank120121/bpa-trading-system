import sqlite3
from prettytable import PrettyTable
import logging
from logging_config import setup_logging
setup_logging(log_filename='Binance_c2c_logger.log')
logger = logging.getLogger(__name__)

DATABASE_PATH = 'C:/Users/p7016/Documents/bpa/asset_balances.db'

def setup_total_balances_db():
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS total_balances (
                asset TEXT PRIMARY KEY,
                total_balance FLOAT
            )
        ''')
        connection.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to create total_balances table, Error: {str(e)}")
    finally:
        if connection:
            connection.close()

def setup_bank_accounts_db():
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS bank_accounts (
                id INTEGER PRIMARY KEY,
                account_number TEXT UNIQUE,
                account_name TEXT,
                bank_name TEXT,
                account_balance FLOAT DEFAULT 0
            )
        ''')
        connection.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to create bank_accounts table, Error: {str(e)}")
    finally:
        if connection:
            connection.close()



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

def add_bank_account(account_number, account_name, bank_name):
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        cursor.execute('''
            INSERT INTO bank_accounts (account_number, account_name, bank_name)
            VALUES (?, ?, ?, ?)
        ''', (account_number, account_name, bank_name))
        connection.commit()
    except sqlite3.IntegrityError:
        logger.error(f"Account number {account_number} already exists.")
    except sqlite3.Error as e:
        logger.error(f"Failed to add bank account {account_number}, Error: {str(e)}")
    finally:
        if connection:
            connection.close()

def update_total_balances():
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()

        # Get the total balances from balances table
        cursor.execute('''
            SELECT asset, SUM(balance)
            FROM balances
            GROUP BY asset
        ''')
        aggregated_balances = cursor.fetchall()

        # Update the total_balances table
        for asset, total_balance in aggregated_balances:
            cursor.execute('''
                INSERT OR REPLACE INTO total_balances (asset, total_balance)
                VALUES (?, ?)
            ''', (asset, total_balance))
        
        connection.commit()
    except sqlite3.Error as e:
        logger.error(f"Failed to update total_balances table, Error: {str(e)}")
    finally:
        if connection:
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
def print_table_contents(table_name):
    try:
        connection = sqlite3.connect(DATABASE_PATH)
        cursor = connection.cursor()
        
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = cursor.fetchall()
        column_names = [column[1] for column in columns_info]

        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        table = PrettyTable()
        table.field_names = column_names
        for row in rows:
            table.add_row(row)
        
        print(f"\nContents of {table_name}:")
        print(table)

    except sqlite3.Error as e:
        print(f"Error reading from table {table_name}: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    # setup_db()
    # setup_bank_accounts_db()
    # setup_total_balances_db()
    # update_total_balances()
    # print_table_contents("bank_accounts")
    # print_table_contents("balances")
    # print_table_contents("total_balances")

    
    add_bank_account()
