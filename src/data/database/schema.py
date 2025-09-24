# bpa/binance_db.py
import aiosqlite
from src.data.database.connection import DB_FILE
from src.utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')


async def remove(conn, orderNumber):
    await conn.execute("DELETE FROM orders WHERE orderNumber = ?", (orderNumber,))
    await conn.commit()
    logger.info(f"Order {orderNumber} removed successfully")

async def remove_user(conn, name):
    await conn.execute("DELETE FROM users WHERE name = ?", (name,))
    await conn.commit()
    logger.info(f"User {name} removed successfully")


# SQL CREATE TABLE statements based on ALLOWED_TABLES structure
CREATE_TABLE_STATEMENTS = {
    "orders": """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orderNumber TEXT UNIQUE NOT NULL,
            advOrderNumber TEXT,
            buyerName TEXT,
            buyerNickname TEXT,
            buyerMobilePhone TEXT,
            sellerName TEXT,
            sellerNickname TEXT,
            sellerMobilePhone TEXT,
            tradeType TEXT,
            orderStatus INTEGER,
            totalPrice REAL,
            price REAL,
            fiatUnit TEXT,
            fiatSymbol TEXT,
            asset TEXT,
            amount REAL,
            payType TEXT,
            selectedPayId INTEGER,
            currencyRate REAL,
            createTime INTEGER,
            notifyPayTime INTEGER,
            confirmPayTime INTEGER,
            notifyPayEndTime INTEGER,
            confirmPayEndTime INTEGER,
            remark TEXT,
            merchantNo TEXT,
            takerUserNo TEXT,
            commission REAL,
            commissionRate REAL,
            takerCommission REAL,
            takerCommissionRate REAL,
            takerAmount REAL,
            menu_presented INTEGER DEFAULT 0,
            ignore_count INTEGER DEFAULT 0,
            account_number TEXT,
            buyer_bank TEXT,
            seller_bank_account TEXT,
            merchant_id INTEGER,
            priceFloatingRatio REAL,
            payment_screenshoot INTEGER DEFAULT 0,
            payment_image_url TEXT,
            paid INTEGER DEFAULT 0,
            clave_de_rastreo TEXT,
            seller_bank TEXT,
            returning_customer_stage INTEGER DEFAULT 0,
            order_date TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (merchant_id) REFERENCES merchants(id)
        )
    """,
    
    "users": """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            kyc_status INTEGER DEFAULT 0,
            total_crypto_sold_lifetime REAL DEFAULT 0.0,
            anti_fraud_stage INTEGER DEFAULT 0,
            rfc TEXT,
            codigo_postal TEXT,
            user_bank TEXT,
            usd_verification_stage INTEGER DEFAULT 0,
            language_preference TEXT,
            language_selection_stage INTEGER DEFAULT 0
        )
    """,
    
    "merchants": """
        CREATE TABLE IF NOT EXISTS merchants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sellerName TEXT UNIQUE NOT NULL,
            api_key TEXT,
            api_secret TEXT,
            email TEXT,
            password_hash TEXT,
            phone_num TEXT,
            user_bank TEXT
        )
    """,
    
    "transactions": """
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            buyer_name TEXT NOT NULL,
            seller_name TEXT NOT NULL,
            total_price REAL NOT NULL,
            order_date TEXT NOT NULL,
            merchant_id INTEGER,
            FOREIGN KEY (merchant_id) REFERENCES merchants(id),
            UNIQUE(buyer_name, seller_name, total_price, order_date)
        )
    """,
    
    "order_bank_identifiers": """
        CREATE TABLE IF NOT EXISTS order_bank_identifiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            orderNumber TEXT NOT NULL,
            bank_identifier TEXT NOT NULL,
            FOREIGN KEY (orderNumber) REFERENCES orders(orderNumber)
        )
    """,
    
    "usd_price_manager": """
        CREATE TABLE IF NOT EXISTS usd_price_manager (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            trade_type TEXT NOT NULL,
            exchange_rate_ratio REAL NOT NULL,
            mxn_amount REAL NOT NULL
        )
    """,
    
    "deposits": """
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            bank_account_id INTEGER NOT NULL,
            amount_deposited REAL NOT NULL,
            FOREIGN KEY (bank_account_id) REFERENCES bank_accounts(id)
        )
    """,
    
    "bank_accounts": """
        CREATE TABLE IF NOT EXISTS bank_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_bank_name TEXT NOT NULL,
            account_beneficiary TEXT NOT NULL,
            account_number TEXT UNIQUE NOT NULL,
            account_limit REAL DEFAULT 0.0,
            account_balance REAL DEFAULT 0.0
        )
    """,
    
    "blacklist": """
        CREATE TABLE IF NOT EXISTS blacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            orderNumber TEXT,
            country TEXT
        )
    """,
    
    "mxn_deposits": """
        CREATE TABLE IF NOT EXISTS mxn_deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            account_number TEXT NOT NULL,
            amount_deposited REAL NOT NULL,
            deposit_from TEXT,
            year INTEGER,
            month INTEGER,
            merchant_id INTEGER,
            FOREIGN KEY (merchant_id) REFERENCES merchants(id)
        )
    """,
    
    "P2PBlacklist": """
        CREATE TABLE IF NOT EXISTS P2PBlacklist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            orderNumber TEXT,
            country TEXT,
            response TEXT,
            anti_fraud_stage INTEGER,
            merchant_id INTEGER,
            FOREIGN KEY (merchant_id) REFERENCES merchants(id)
        )
    """,
    
    "mxn_bank_accounts": """
        CREATE TABLE IF NOT EXISTS mxn_bank_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_bank_name TEXT NOT NULL,
            account_beneficiary TEXT NOT NULL,
            account_number TEXT UNIQUE NOT NULL,
            account_daily_limit REAL DEFAULT 0.0,
            account_monthly_limit REAL DEFAULT 0.0,
            account_balance REAL DEFAULT 0.0,
            last_used_timestamp TEXT,
            merchant_id INTEGER,
            FOREIGN KEY (merchant_id) REFERENCES merchants(id)
        )
    """,
    
    "oxxo_debit_cards": """
        CREATE TABLE IF NOT EXISTS oxxo_debit_cards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_bank_name TEXT NOT NULL,
            account_beneficiary TEXT NOT NULL,
            card_number TEXT UNIQUE NOT NULL,
            account_daily_limit REAL DEFAULT 0.0,
            account_monthly_limit REAL DEFAULT 0.0,
            account_balance REAL DEFAULT 0.0,
            last_used_timestamp TEXT,
            merchant_id INTEGER,
            FOREIGN KEY (merchant_id) REFERENCES merchants(id)
        )
    """
}

async def create_all_tables():
    """Create all tables defined in ALLOWED_TABLES"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            # Enable foreign key constraints
            await conn.execute("PRAGMA foreign_keys = ON")
            
            logger.info("Starting table creation process...")
            
            # Create tables in order (merchants first due to foreign key dependencies)
            table_order = [
                "merchants", "users", "bank_accounts", "orders", "transactions",
                "order_bank_identifiers", "usd_price_manager", "deposits",
                "blacklist", "mxn_deposits", "P2PBlacklist", "mxn_bank_accounts",
                "oxxo_debit_cards"
            ]
            
            for table_name in table_order:
                if table_name in CREATE_TABLE_STATEMENTS:
                    try:
                        await conn.execute(CREATE_TABLE_STATEMENTS[table_name])
                        logger.info(f"Table '{table_name}' created successfully")
                    except Exception as e:
                        logger.error(f"Error creating table '{table_name}': {e}")
                        raise
            
            await conn.commit()
            logger.info("All tables created successfully!")
            
            # Verify tables were created
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = await cursor.fetchall()
                logger.info(f"Current tables in database: {[table[0] for table in tables]}")
                
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        raise

async def drop_all_tables():
    """Drop all tables (use with caution!)"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            logger.warning("DROPPING ALL TABLES - THIS WILL DELETE ALL DATA!")
            
            # Get all table names
            async with conn.cursor() as cursor:
                await cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = await cursor.fetchall()
            
            # Drop tables in reverse dependency order
            for table in reversed(CREATE_TABLE_STATEMENTS.keys()):
                try:
                    await conn.execute(f"DROP TABLE IF EXISTS {table}")
                    logger.info(f"Table '{table}' dropped")
                except Exception as e:
                    logger.error(f"Error dropping table '{table}': {e}")
            
            await conn.commit()
            logger.info("All tables dropped successfully!")
            
    except Exception as e:
        logger.error(f"Error dropping tables: {e}")
        raise

async def check_table_structure():
    """Check the structure of all tables"""
    try:
        async with aiosqlite.connect(DB_FILE) as conn:
            for table_name in CREATE_TABLE_STATEMENTS.keys():
                logger.info(f"\n=== Structure of table '{table_name}' ===")
                try:
                    async with conn.cursor() as cursor:
                        await cursor.execute(f"PRAGMA table_info({table_name})")
                        columns = await cursor.fetchall()
                        if columns:
                            for col in columns:
                                logger.info(f"  {col[1]} ({col[2]}) - {'NOT NULL' if col[3] else 'NULL'}")
                        else:
                            logger.warning(f"Table '{table_name}' does not exist")
                except Exception as e:
                    logger.error(f"Error checking table '{table_name}': {e}")
                    
    except Exception as e:
        logger.error(f"Error checking table structures: {e}")
        raise