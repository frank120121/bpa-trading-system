# bpa/binance_bank_deposit.py
import asyncio
from typing import Dict, Optional, Any

from src.data.database.operations.binance_db_get import get_order_details
from src.data.database.operations.binance_db_set import update_order_details
from src.data.database.deposits.binance_bank_deposit_db import update_last_used_timestamp, sum_recent_deposits, sum_monthly_deposits
import logging
from src.utils.logging_config import setup_logging

setup_logging(log_filename='binance_main.log')
logger = logging.getLogger(__name__)



# --- Start of New Buyer Limit Constants ---
USD_BUYER_DAILY_LIMIT = 950.00
MXN_BUYER_MONTHLY_LIMIT = 75000.00
# --- End of New Buyer Limit Constants ---

class PaymentManager:
    _instance: Optional['PaymentManager'] = None
    _lock = asyncio.Lock()

    def __init__(self):
        if self.__class__._instance is not None:
            raise RuntimeError("This class is a singleton. Use get_instance() instead.")
        self.accounts_cache: Dict[str, list] = {}
        self.accounts_cache_lock = asyncio.Lock()

    @classmethod
    async def get_instance(cls) -> 'PaymentManager':
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    async def initialize_payment_account_cache(self, conn):
        """Populates the cache with all payment accounts, grouped by pay_type."""
        async with self.accounts_cache_lock:
            cursor = await conn.execute('SELECT fiat, pay_type, beneficiary, account_details, daily_limit, monthly_limit FROM payment_accounts ORDER BY last_used_timestamp ASC')
            all_accounts = await cursor.fetchall()
            self.accounts_cache = {}
            for acc in all_accounts:
                pay_type = acc[1]
                if pay_type not in self.accounts_cache:
                    self.accounts_cache[pay_type] = []
                
                account_data = {
                    'fiat': acc[0], 'pay_type': acc[1], 'beneficiary': acc[2],
                    'account_details': acc[3], 'daily_limit': acc[4], 'monthly_limit': acc[5]
                }
                self.accounts_cache[pay_type].append(account_data)
            logger.info(f"Initialized payment account cache with {len(all_accounts)} accounts.")

    async def get_payment_details(self, conn, orderNumber: str, buyerName: str) -> Optional[Dict[str, Any]]:
        """Main entry point to get payment details based on order context."""
        order = await get_order_details(conn, orderNumber)
        if not order:
            logger.error(f"Could not retrieve details for order {orderNumber}")
            return None
        logger.info(f"Retrieved order details: {order}")
        payType = order.get('payType') 
        amount_to_deposit = order.get('totalPrice', 0.0)

        return await self._assign_account(conn, payType, orderNumber, buyerName, amount_to_deposit)

    async def _assign_account(self, conn, pay_type: str, orderNumber: str, buyerName: str, amount: float) -> Optional[Dict[str, Any]]:
        """
        Assigns the best available account for any currency by checking limits
        and selecting the one with the lowest current daily balance.
        """
        async with self.accounts_cache_lock:
            accounts = self.accounts_cache.get(pay_type, [])
            if not accounts:
                logger.warning(f"No accounts found for pay_type: {pay_type}")
                return None

            valid_accounts = []
            for account in accounts:
                if await self._check_deposit_limit(conn, account, amount, buyerName):
                    daily_total = await sum_recent_deposits(conn, account['account_details'])
                    valid_accounts.append((account, daily_total))
            
            if not valid_accounts:
                logger.warning(f"All accounts for {pay_type} are over the limit for order {orderNumber}.")
                return None

            valid_accounts.sort(key=lambda x: x[1])
            best_account = valid_accounts[0][0]
            
            await update_order_details(conn, orderNumber, best_account['account_details'], best_account['pay_type'])
            await update_last_used_timestamp(conn, best_account['account_details'])
            logger.info(f"Assigned account {best_account['account_details']} for order {orderNumber}")
            return self._format_details(best_account, orderNumber)

    async def _check_deposit_limit(self, conn, account: Dict, amount_to_deposit: float, buyerName: str) -> bool:
        """
        Checks all account and buyer-specific limits based on the account's currency.
        """
        account_details = account['account_details']
        fiat = account['fiat']
        amount_to_add = amount_to_deposit or 0.0

        # --- Step 1: Check the account's own hard limits ---
        daily_total = await sum_recent_deposits(conn, account_details)
        if daily_total + amount_to_add > account['daily_limit']:
            logger.info(f"Account {account_details} would exceed its daily limit of {account['daily_limit']}.")
            return False

        monthly_total = await sum_monthly_deposits(conn, account_details)
        if monthly_total + amount_to_add > account['monthly_limit']:
            logger.info(f"Account {account_details} would exceed its monthly limit of {account['monthly_limit']}.")
            return False
            
        # --- Step 2: Check the buyer's currency-specific limits ---
        if fiat == 'USD':
            # For USD, check the buyer's daily limit
            buyer_daily_total = await sum_recent_deposits(conn, account_details, buyerName)
            if buyer_daily_total + amount_to_add > USD_BUYER_DAILY_LIMIT:
                logger.warning(f"Buyer '{buyerName}' would exceed their daily USD limit of ${USD_BUYER_DAILY_LIMIT}.")
                return False
        
        elif fiat == 'MXN':
            # For MXN, check the buyer's monthly limit
            buyer_monthly_total = await sum_monthly_deposits(conn, account_details, buyerName)
            if buyer_monthly_total + amount_to_add > MXN_BUYER_MONTHLY_LIMIT:
                logger.warning(f"Buyer '{buyerName}' would exceed their monthly MXN limit of ${MXN_BUYER_MONTHLY_LIMIT}.")
                return False

        return True

    def _format_details(self, account: Dict, orderNumber: Optional[str] = None) -> str:
        """Formats the payment details for the user message based on the pay_type."""
        fiat = account['fiat']
        pay_type = account['pay_type']
        details = account['account_details']
        beneficiary = account['beneficiary']

        if pay_type == 'OXXO':
            return (
                f"Muestra el numero de tarjeta de debito junto con el efectivo que vas a depositar:\n\n"
                f"Recuerda que solo se acepta deposito en efectivo.\n\n"
                f"Número de tarjeta de debito: {details}"
            )
        elif fiat == 'USD':
            return (
                f"Please send the payment to the following {pay_type} account:\n\n"
                f"Beneficiary: {beneficiary}\n"
                f"Email/Phone: {details}"
            )
        else: # Default to MXN Bank Transfer format
            return (
                f"Los detalles para el pago son:\n\n"
                f"Nombre de banco: {pay_type}\n"
                f"Nombre del beneficiario: {beneficiary}\n"
                f"Número de CLABE: {details}\n"
                f"Concepto: {orderNumber}\n\n"
                f"Por favor, incluye el concepto de arriba en tu pago."
            )