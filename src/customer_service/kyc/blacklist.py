import aiosqlite

async def initialize_database(conn):
    await conn.execute(
        """
        CREATE TABLE IF NOT EXISTS P2PBlacklist (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE,
            order_no TEXT,
            country TEXT,
            response TEXT DEFAULT NULL,
            anti_fraud_stage INTEGER DEFAULT 0,
            merchant_id INTEGER REFERENCES merchants(id)
        )
        """
    )
    await conn.commit()

async def clear_blacklist(conn):
    await conn.execute("DELETE FROM P2PBlacklist")
    await conn.commit()

# Modify the function to accept response and anti_fraud_stage, both of which are optional
async def add_to_blacklist(conn, name, order_no, country, response=None, anti_fraud_stage=0, merchant_id=None):
    try:
        await conn.execute(
            "INSERT OR IGNORE INTO P2PBlacklist (name, order_no, country, response, anti_fraud_stage, merchant_id) VALUES (?, ?, ?, ?, ?, ?)", 
            (name, order_no, country, response, anti_fraud_stage, merchant_id)
        )
        await conn.commit()
    except aiosqlite.IntegrityError:
        pass

async def is_blacklisted(conn, name):
    cursor = await conn.execute("SELECT id FROM P2PBlacklist WHERE name = ?", (name,))
    result = await cursor.fetchone()
    return result is not None

async def remove_from_blacklist(conn, name):
    await conn.execute("DELETE FROM P2PBlacklist WHERE name = ?", (name,))
    await conn.commit()

# Make an async function that removes users from the blacklist whose country is none
async def remove_from_blacklist_no_country(conn):
    await conn.execute("DELETE FROM P2PBlacklist WHERE country IS NULL")
    await conn.commit()
    
async def get_blacklist_counts_by_country(conn):
    query = """
    SELECT country, COUNT(*) as count
    FROM P2PBlacklist
    GROUP BY country
    """
    async with conn.execute(query) as cursor:
        result = await cursor.fetchall()
        return result

async def remove_from_blacklist_accepted_countries(conn, accepted_countries):
    placeholders = ', '.join('?' for _ in accepted_countries)
    query = f"DELETE FROM P2PBlacklist WHERE country IN ({placeholders})"
    await conn.execute(query, accepted_countries)
    await conn.commit()

# New function to update the merchant_id for a given order_no
async def update_merchant_id(conn, order_no, merchant_id):
    await conn.execute(
        "UPDATE P2PBlacklist SET merchant_id = ? WHERE order_no = ?",
        (merchant_id, order_no)
    )
    await conn.commit()

accepted_countries_for_oxxo = ['MX', 'CO', 'VE', 'AR', 'ES', 'CL', 'CA', 'HK', 'PE', 'BE', 'EC', 'RU', 'TH', 'IN', 'UA', 'DE', 'JP', 'US', 'RU', 'FR']