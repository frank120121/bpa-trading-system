import aiosqlite
import asyncio
import logging
from prettytable import PrettyTable
logger = logging.getLogger(__name__)
async def create_connection(db_file, num_retries=3, delay_seconds=5):
    logger.debug("Inside async_create_connection function")
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

async def print_table_contents(conn, table_name):
    async with conn.cursor() as cursor:
        try:
            await cursor.execute(f"PRAGMA table_info({table_name})")
            columns_info = await cursor.fetchall()
            column_names = [column[1] for column in columns_info]
            await cursor.execute(f"SELECT * FROM {table_name}")
            rows = await cursor.fetchall()
            table = PrettyTable()
            table.field_names = column_names
            for row in rows:
                table.add_row(row)
            print(f"\nContents of {table_name}:")
            print(table)
        except Exception as e:
            print(f"Error reading from table {table_name}: {e}")
async def add_column_if_not_exists(conn, table_name, column_definition):
    async with conn.cursor() as cursor:
        await cursor.execute(f"PRAGMA table_info({table_name})")
        columns_info = await cursor.fetchall()
        column_names = [column[1] for column in columns_info]

        if column_definition.split()[0] not in column_names:
            alter_table_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_definition}"
            await cursor.execute(alter_table_sql)

async def add_column_if_not_exists(conn, table_name, column_name, column_type):
    column_exists_query = f"PRAGMA table_info({table_name})"
    cursor = await conn.execute(column_exists_query)
    columns_info = await cursor.fetchall()
    if column_name not in [col[1] for col in columns_info]:  # Column names are in the second position
        alter_table_query = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
        await conn.execute(alter_table_query)
        logger.info(f"Added '{column_name}' column to '{table_name}' table.")