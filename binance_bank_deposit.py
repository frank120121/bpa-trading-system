import datetime
import logging
from binance_db_get import get_buyer_bank, get_order_amount, get_buyer_name
from binance_db_set import update_order_details
from binance_bank_deposit_db import update_last_used_timestamp

logger = logging.getLogger(__name__)

async def check_deposit_limit(conn, account_number, order_no, monthly_limit=70000.00):
    # Get the current month and year
    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year

    # Get the buyer's name for the order
    buyer_name = await get_buyer_name(conn, order_no)

    # Get the amount to deposit from the current order
    amount_to_deposit = await get_order_amount(conn, order_no)

    # Query to calculate the sum of deposits made to the account by this buyer in the current month
    query = '''
        SELECT SUM(amount_deposited)
        FROM mxn_deposits
        WHERE account_number = ? AND deposit_from = ? AND year = ? AND month = ?
    '''

    cursor = await conn.execute(query, (account_number, buyer_name, current_year, current_month))
    total_deposited_this_month = await cursor.fetchone()
    total_deposited_this_month = total_deposited_this_month[0] if total_deposited_this_month[0] is not None else 0

    # Calculate the total after the proposed deposit
    total_after_deposit = total_deposited_this_month + amount_to_deposit

    # Log the current total and the total after deposit
    logger.info(f"Buyer '{buyer_name}' has already deposited {total_deposited_this_month:.2f} to account {account_number} this month.")
    logger.info(f"After the deposit of {amount_to_deposit:.2f}, the total will be {total_after_deposit:.2f}.")

    # Check if adding the new deposit exceeds the monthly limit
    if total_after_deposit <= monthly_limit:
        return True  # The deposit does not exceed the limit
    else:
        logger.warning(f"Deposit exceeds the monthly limit of {monthly_limit:.2f} for buyer '{buyer_name}' on account {account_number}.")
        return False
      
async def find_suitable_account(conn, buyer_bank, ignore_bank_preference=False):
    current_date = datetime.datetime.now().date()
    current_month_str = datetime.datetime.now().strftime("%m")
    current_date_str = current_date.strftime('%Y-%m-%d')

    # If ignoring bank preference, do not add a bank name condition to the query
    buyer_bank_condition = "" if ignore_bank_preference or buyer_bank is None else f"AND LOWER(a.account_bank_name) = '{buyer_bank.lower()}'"

    query = f'''
        SELECT a.account_number, a.account_bank_name, a.account_balance
        FROM mxn_bank_accounts a
        LEFT JOIN (
            SELECT account_number, SUM(amount_deposited) AS total_deposited_today
            FROM mxn_deposits
            WHERE DATE(timestamp) = ?
            GROUP BY account_number
        ) d ON a.account_number = d.account_number
        LEFT JOIN (
            SELECT account_number, SUM(amount_deposited) AS total_deposited_this_month
            FROM mxn_deposits
            WHERE strftime('%m', timestamp) = ?
            GROUP BY account_number
        ) m ON a.account_number = m.account_number
        WHERE (d.total_deposited_today < a.account_daily_limit OR d.total_deposited_today IS NULL)
        AND (m.total_deposited_this_month < a.account_monthly_limit OR m.total_deposited_this_month IS NULL)
        AND a.account_balance < a.account_monthly_limit
        {buyer_bank_condition}
        ORDER BY a.last_used_timestamp ASC, a.account_balance ASC
    '''

    cursor = await conn.execute(query, (current_date_str, current_month_str))
    accounts = await cursor.fetchall()
    return [acc[0] for acc in accounts] 


async def get_payment_details(conn, order_no):
    # Check if a bank account has already been assigned to the order_no
    cursor = await conn.execute('SELECT account_number FROM orders WHERE order_no = ?', (order_no,))
    result = await cursor.fetchone()
    assigned_account_number = result[0] if result else None

    if assigned_account_number:
        logger.info(f"Account already assigned for order {order_no}.")
        return await get_account_details(conn, assigned_account_number)

    buyer_bank = await get_buyer_bank(conn, order_no)
    suitable_accounts = await find_suitable_account(conn, buyer_bank, ignore_bank_preference=False)

    # If no account matches the buyer's bank preference or buyer_bank is None, search without bank preference
    if not suitable_accounts:
        suitable_accounts = await find_suitable_account(conn, buyer_bank, ignore_bank_preference=True)

    for account_number in suitable_accounts:
        if await check_deposit_limit(conn, account_number, order_no):
            await update_order_details(conn, order_no, account_number)
            await update_last_used_timestamp(conn, account_number)
            return await get_account_details(conn, account_number)
        else:
            logger.info(f"Account {account_number} exceeded the monthly deposit limit for the buyer.")

    return "Sorry, no bank accounts available at this time or all suitable accounts exceed the monthly limit."


async def get_account_details(conn, account_number):
    logger.info(f"Retrieving details for account {account_number}")
    cursor = await conn.execute('SELECT account_bank_name, account_beneficiary, account_number FROM mxn_bank_accounts WHERE account_number = ?', (account_number,))
    account_details = await cursor.fetchone()
    if account_details:
        logger.info(f"Details retrieved for account {account_number}")
        account_label = "Número de cuenta" if account_details[0].lower() == "bbva" else "Número de CLABE"
        return (
            f"Los detalles para el pago son:\n\n"
            f"Nombre de banco: {account_details[0]}\n"
            f"Nombre del beneficiario: {account_details[1]}\n"
            f"{account_label}: {account_details[2]}\n"
        )
    else:
        logger.warning(f"No details found for account {account_number}")
        return None