import datetime
import random
import logging
from database import get_buyer_bank, update_order_details
from common_vars import BBVA_BANKS

logger = logging.getLogger(__name__)

MONTHLY_DEPOSIT_LIMIT = 60000.00

async def log_deposit(conn, deposit_from, bank_account_number, amount_deposited):
    timestamp = datetime.datetime.now()
    year, month = timestamp.year, timestamp.month 
    await conn.execute('INSERT INTO mxn_deposits (timestamp, account_number, amount_deposited, deposit_from, year, month) VALUES (?, ?, ?, ?, ?, ?)',
                       (timestamp, bank_account_number, amount_deposited, deposit_from, year, month))
    await conn.execute('UPDATE mxn_bank_accounts SET account_balance = account_balance + ? WHERE account_number = ?', (amount_deposited, bank_account_number))
    await conn.commit()

async def get_payment_details(conn, order_no, buyer_name):
    cutoff_time = datetime.datetime.now() - datetime.timedelta(days=1)
    month_start = datetime.datetime(datetime.datetime.now().year, datetime.datetime.now().month, 1)
    cursor = await conn.execute('SELECT account_number FROM orders WHERE order_no = ?', (order_no,))
    result = await cursor.fetchone()
    assigned_account_number = result[0] if result else None

    if assigned_account_number:
        logger.info(f"Account already assigned for order {order_no}.")
        return await get_account_details(conn, assigned_account_number)

    buyer_bank = await get_buyer_bank(conn, order_no)
    is_bbva_bank = buyer_bank in BBVA_BANKS if buyer_bank else False
    bank_condition = 'LIKE' if is_bbva_bank else 'NOT LIKE'
    
    accounts = await get_eligible_accounts(conn, bank_condition)
    if not accounts:
        logger.info("No eligible accounts found.")
        return "All accounts have reached their limit, or the user has reached the monthly limit on all accounts."

    # Shuffle the accounts list to ensure random selection
    random.shuffle(accounts)

    deposit_sums = await get_deposit_sums(conn, cutoff_time, month_start)

    for account in accounts:
        if is_account_eligible(account, deposit_sums, buyer_name):
            assigned_account_number = account[3]
            await conn.execute('UPDATE mxn_bank_accounts SET last_used_timestamp = ? WHERE account_number = ?', (datetime.datetime.now(), assigned_account_number))
            await update_order_details(conn, order_no, assigned_account_number)
            logger.info(f"Account {assigned_account_number} assigned to order {order_no}.")
            return await get_account_details(conn, assigned_account_number)

    logger.info("All accounts have reached their limit, or the user has reached the monthly limit on all accounts.")
    return "Reached their limit."
async def get_eligible_accounts(conn, bank_condition):
    query = f"SELECT id, account_bank_name, account_beneficiary, account_number, account_limit FROM mxn_bank_accounts WHERE account_bank_name {bank_condition} '%BBVA%' ORDER BY id"
    cursor = await conn.execute(query)
    return await cursor.fetchall()

def is_account_eligible(account, deposit_sums, buyer_name):
    account_number = account[3]
    total_deposited_24h = deposit_sums['24h'].get(account_number, 0)
    if total_deposited_24h >= account[4]:
        return False

    monthly_total_deposited_by_buyer = deposit_sums['monthly'][account_number].get(buyer_name, 0)
    if monthly_total_deposited_by_buyer >= MONTHLY_DEPOSIT_LIMIT:
        return False

    return True

async def get_deposit_sums(conn, cutoff_time, month_start):
    # Query to sum deposits in the last 24 hours for each account
    cursor = await conn.execute('SELECT account_number, SUM(amount_deposited) FROM mxn_deposits WHERE timestamp >= ? GROUP BY account_number', (cutoff_time,))
    deposits_24h = {row[0]: row[1] for row in await cursor.fetchall()}

    # Query to sum monthly deposits for each buyer to each account
    cursor = await conn.execute('SELECT account_number, deposit_from, SUM(amount_deposited) FROM mxn_deposits WHERE timestamp >= ? GROUP BY account_number, deposit_from', (month_start,))
    deposits_monthly = {}
    for account_number, buyer, sum_ in await cursor.fetchall():
        if account_number not in deposits_monthly:
            deposits_monthly[account_number] = {}
        deposits_monthly[account_number][buyer] = sum_

    return {'24h': deposits_24h, 'monthly': deposits_monthly}

async def get_account_details(conn, account_number):
    cursor = await conn.execute('SELECT account_bank_name, account_beneficiary, account_number FROM mxn_bank_accounts WHERE account_number = ?', (account_number,))
    account_details = await cursor.fetchone()
    if account_details:
        return (
            f"Los detalles para el pago son:\n\n"
            f"Nombre de banco: {account_details[0]}\n"
            f"Nombre del beneficiario: {account_details[1]}\n"
            f"Número de CLABE: {account_details[2]}\n"
        )