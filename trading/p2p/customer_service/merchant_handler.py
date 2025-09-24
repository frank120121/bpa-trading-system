# bpa/binance_merchant_handler.py
import json
import traceback
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass

from data.cache.order_cache import OrderCache
from trading.p2p.payment_verification.spei_validation import TransferValidationQueue, TransferValidator
from data.database.operations.binance_db_set import insert_or_update_order
from trading.p2p.kyc.binance_language_selection import LanguageSelector

from localization.lang_utils import (
    get_message_by_language, get_default_help, 
    verified_customer_greeting, transaction_denied,
    get_response_for_menu_choice, is_valid_choice,
    get_invalid_choice_reply, get_menu_for_order,
    determine_language
)
from data.database.operations.binance_db_get import (
    get_account_number, is_menu_presented, get_kyc_status,
    get_anti_fraud_stage, get_buyer_bank, get_order_details,
    get_returning_customer_stage
)

from data.database.operations.binance_db_set import (
    update_order_status, update_total_spent, update_buyer_bank,
    set_menu_presented
)
from data.database.deposits.binance_bank_deposit_db import log_deposit
from exchanges.binance.orders import binance_buy_order
from trading.p2p.binance_anti_fraud import handle_user_verification
from trading.p2p.kyc.blacklist import is_blacklisted
from utils.common_vars import status_map
from utils.common_utils import send_messages
from trading.p2p.customer_service.returning_customer import returning_customer
from utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

@dataclass
class OrderData:
    orderNumber: str
    buyerName: str
    sellerName: str
    tradeType: str
    fiatUnit: str
    totalPrice: float
    asset: str
    orderStatus: int
    account_number: str
    buyer_bank: Optional[str] = None
    payType: Optional[str] = None
    returning_customer_stage: int = 0

class MerchantAccount:
    def __init__(self, payment_manager, binance_api):
        self.payment_manager = payment_manager
        self.binance_api = binance_api
        self.validation_queue = TransferValidationQueue()
        self.validator = None

    def initialize_validator(self, connection_manager) -> None:
        """Initialize the transfer validator with the connection manager."""
        self.validator = TransferValidator(self.validation_queue, connection_manager)

    async def start_validation_processor(self):
        """Start the validation processor task."""
        if self.validator is None:
            raise ValueError("Validator not initialized. Call initialize_validator first.")
        return asyncio.create_task(self.validator.process_queue())

    def _extract_order_data(self, order_details: Dict[str, Any], orderNumber: str) -> OrderData:
        """Extract order data from order details dictionary."""
        return OrderData(
            orderNumber=orderNumber,
            buyerName=order_details.get('buyerName', ''),
            sellerName=order_details.get('sellerName', ''),
            tradeType=order_details.get('tradeType', ''),
            fiatUnit=order_details.get('fiatUnit', ''),
            totalPrice=order_details.get('totalPrice', 0.0),
            asset=order_details.get('asset', ''),
            orderStatus=order_details.get('orderStatus', 0),
            account_number=order_details.get('account_number', ''),
            buyer_bank=order_details.get('buyer_bank', None),
            payType=order_details.get('payType', None),
            returning_customer_stage=order_details.get('returning_customer_stage', 0)
        )

    async def _fetch_and_update_order_details(
        self,
        KEY: str,
        SECRET: str,
        conn,
        orderNumber: str
    ) -> Optional[Dict[str, Any]]:
        """Fetch and update order details with intelligent caching."""
        try:
            # Check cache first
            order_details = await OrderCache.get_order(orderNumber)
            
            if not order_details:
                # Not in cache, check DB
                order_details = await get_order_details(conn, orderNumber)
                
                if order_details:
                    # Check if it's a terminal state - don't cache these
                    orderStatus = order_details.get('orderStatus', 0)
                    if orderStatus not in [4, 6, 7]:
                        # Only cache active orders
                        await OrderCache.set_order(orderNumber, order_details)
                        logger.debug(f"Cached active order {orderNumber}")
                    else:
                        logger.debug(f"Order {orderNumber} is in terminal state {orderStatus}, not caching")
                else:
                    # Not in DB either, fetch from API
                    order_details = await self.binance_api.fetch_order_details(KEY, SECRET, orderNumber)
                    if order_details:
                        await insert_or_update_order(conn, order_details)
                        order_details = await get_order_details(conn, orderNumber)
                        
                        # Cache if not terminal
                        orderStatus = order_details.get('orderStatus', 0)
                        if orderStatus not in [4, 6, 7]:
                            await OrderCache.set_order(orderNumber, order_details)
            
            return order_details
            
        except Exception as e:
            logger.error(f"Error fetching order details: {str(e)}\n{traceback.format_exc()}")
            return None

    # ==========================================
    # MAIN MESSAGE HANDLING
    # ==========================================

    async def handle_message_by_type(
        self,
        connection_manager,
        account: str,
        KEY: str,
        SECRET: str,
        msg_json: Dict[str, Any],
        conn
    ) -> None:
        """Handle incoming messages based on their type."""
        try:
            order_details = await self._fetch_and_update_order_details(
                KEY, SECRET, conn, msg_json.get('orderNo', '')
            )
            if not order_details:
                logger.warning("Failed to fetch order details")
                return
            order_data = self._extract_order_data(order_details, msg_json.get('orderNo', ''))

            if msg_json.get('type') == 'system':
                await self._handle_system_type(connection_manager, account, msg_json, conn, order_data)
            else:
                await self._handle_other_types(connection_manager, account, msg_json, conn, order_data)

        except Exception as e:
            logger.error(f"Error in message handling: {str(e)}\n{traceback.format_exc()}")

    async def _handle_system_type(
        self,
        connection_manager,
        account: str,
        msg_json: Dict[str, Any],
        conn,
        order_data: OrderData
    ) -> None:
        """Handle system type messages."""
        try:
            content = msg_json.get('content', '').lower()
            content_dict = json.loads(content)
            system_type_str = content_dict.get('type', '')
            
            if system_type_str not in status_map:
                logger.info(f"Unknown system type: {system_type_str}")
                return

            orderStatus = status_map[system_type_str]
            await update_order_status(conn, order_data.orderNumber, orderStatus)
            order_data.orderStatus = orderStatus
            await self.handle_system_notifications(
                connection_manager,
                account,
                order_data,
                conn,
                orderStatus
            )

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}\nContent: {content}")
        except Exception as e:
            logger.error(f"System type handling error: {str(e)}\n{traceback.format_exc()}")

    async def _handle_other_types(
        self,
        connection_manager,
        account: str,
        msg_json: Dict[str, Any],
        conn,
        order_data: OrderData
    ) -> None:
        """Handle non-system type messages."""
        try:
            customer_name = order_data.sellerName if order_data.tradeType == 'BUY' else order_data.buyerName
            
            if await is_blacklisted(conn, customer_name):
                logger.info(f"Blacklisted customer: {customer_name}")
                return
                
            # Early return conditions
            if (msg_json.get('status') == 'read'
                or msg_json.get('uuid', '').startswith("self_")):
                return

            msg_type = msg_json.get('type')
            if msg_type == 'text':
                content = msg_json.get('content', '').lower()
                await self.handle_text_message(
                    connection_manager,
                    account,
                    content,
                    order_data,
                    conn
                )
            elif msg_type == 'image':
                await self.handle_image_message(
                    connection_manager,
                    account,
                    msg_json,
                    order_data,
                    conn
                )

        except Exception as e:
            logger.error(f"Message handling error: {str(e)}\n{traceback.format_exc()}")

    # ==========================================
    # SYSTEM NOTIFICATIONS
    # ==========================================

    async def handle_system_notifications(
        self,
        connection_manager,
        account: str,
        order_data: OrderData,
        conn,
        orderStatus: int
    ) -> None:
        """Handle system notifications based on order status."""
        try:
            # Define terminal states
            TERMINAL_STATES = [4, 6]
            
            # Handle BUY orders differently - we are the buyer, customer is the seller
            if order_data.tradeType == 'BUY':
                if orderStatus == 3:
                    await self._handle_order_status_3(connection_manager, account, conn, order_data)
                elif orderStatus == 4:
                    await self._handle_order_status_4_buy(connection_manager, account, conn, order_data)
                else:
                    await self._generic_reply_buy(connection_manager, account, order_data, orderStatus, conn)
                    
                    # Get language for default reply (use determine_language since we don't store seller preferences)
                    language_for_reply = determine_language(order_data.fiatUnit)
                    
                    user_help = await get_default_help(language_for_reply)
                    await connection_manager.send_text_message(account, user_help, order_data.orderNumber)
            else:
                # Original SELL logic - we are the seller, customer is the buyer
                if orderStatus == 4:
                    await self._handle_order_status_4(connection_manager, account, conn, order_data)
                elif orderStatus == 1:
                    await self._handle_order_status_1(connection_manager, account, conn, order_data)
                else:
                    await self._generic_reply(connection_manager, account, order_data, orderStatus, conn)
                    
                    # Get user's language for default reply
                    user_language = await LanguageSelector.check_language_preference(conn, order_data.buyerName)
                    language_for_reply = user_language or determine_language(order_data.fiatUnit)
                    
                    user_help = await get_default_help(language_for_reply)
                    await connection_manager.send_text_message(account, user_help, order_data.orderNumber)
            
            # Clean up cache for terminal states
            if orderStatus in TERMINAL_STATES:
                await OrderCache.sync_to_db(conn, order_data.orderNumber)
                await OrderCache.remove_order(order_data.orderNumber)
                logger.info(f"Order {order_data.orderNumber} reached terminal state {orderStatus}, removed from cache")

        except Exception as e:
            logger.error(f"System notification error: {str(e)}\n{traceback.format_exc()}")

    # ==========================================
    # STATUS HANDLERS FOR SELL ORDERS
    # ==========================================

    async def _handle_order_status_1(
        self,
        connection_manager,
        account: str,
        conn,
        order_data: OrderData
    ) -> None:
        """Handle order status 1 (initial state) for SELL orders."""
        try:
            if await is_blacklisted(conn, order_data.buyerName):
                await connection_manager.send_text_message(
                    account,
                    transaction_denied,
                    order_data.orderNumber
                )
                logger.info(f"Blacklisted buyer: {order_data.buyerName}")
                return
            
            kyc_status = await get_kyc_status(conn, order_data.buyerName)
            
            # Handle special payType case
            if order_data.payType in ['OXXO', 'Zelle', 'SkrillMoneybookers']:
                await update_buyer_bank(conn, order_data.buyerName, order_data.payType)

            # ALL new customers go through verification
            if kyc_status == 0 or kyc_status is None:
                # Check language preference first using the new module
                language_is_set, language_code = await LanguageSelector.ensure_language_set(
                    conn, order_data.buyerName, connection_manager, account, order_data.orderNumber
                )
                
                # Only proceed to verification if language is already set
                if language_is_set:
                    anti_fraud_stage = await get_anti_fraud_stage(conn, order_data.buyerName) or 0
                    await self._generic_reply(connection_manager, account, order_data, 1, conn)
                    await handle_user_verification(
                        order_data.buyerName,
                        order_data.sellerName,
                        conn,
                        anti_fraud_stage,
                        "",
                        order_data.orderNumber,
                        connection_manager,
                        account,
                        self.payment_manager,
                        order_data.fiatUnit,
                        order_data.payType 
                    )
                else:
                    logger.info('language not set')
            else:
                # Handle verified customer flow
                buyer_bank = await get_buyer_bank(conn, order_data.buyerName)
                
                # Get user's language for greeting
                language = await LanguageSelector.check_language_preference(conn, order_data.buyerName)
                
                greeting = await verified_customer_greeting(order_data.buyerName, language)
                await connection_manager.send_text_message(account, greeting, order_data.orderNumber)
                
                returning_customer_stage = await get_returning_customer_stage(conn, order_data.orderNumber)
                await returning_customer(
                    order_data.buyerName,
                    conn,
                    returning_customer_stage,
                    "",
                    order_data.orderNumber,
                    connection_manager,
                    account,
                    self.payment_manager,
                    buyer_bank,
                    order_data.fiatUnit,
                    order_data.payType
                )

        except Exception as e:
            logger.error(f"Error handling order status 1: {str(e)}\n{traceback.format_exc()}")

    async def _handle_order_status_4(
        self,
        connection_manager,
        account: str,
        conn,
        order_data: OrderData
    ) -> None:
        """Handle order status 4 (completion) for SELL orders."""
        try:
            await self._generic_reply(connection_manager, account, order_data, 4, conn)
            
            if order_data.asset in ['BTC', 'ETH']:
                await binance_buy_order(order_data.asset)
            
            await update_total_spent(conn, order_data.orderNumber)
            bank_account_number = await get_account_number(conn, order_data.orderNumber)
            await log_deposit(
                conn,
                order_data.buyerName,
                bank_account_number,
                order_data.totalPrice
            )

        except Exception as e:
            logger.error(f"Error handling order status 4: {str(e)}\n{traceback.format_exc()}")

    # ==========================================
    # STATUS HANDLERS FOR BUY ORDERS
    # ==========================================

    async def _handle_order_status_3(
        self,
        connection_manager,
        account: str,
        conn,
        order_data: OrderData
    ) -> None:
        """Handle order status 3 for BUY orders - we are the buyer, customer is the seller."""
        try:
            await self._generic_reply_buy(connection_manager, account, order_data, 3, conn)
            
            # Get language for default reply (use determine_language since we don't store seller preferences)
            language_for_reply = determine_language(order_data.fiatUnit)
            
            user_help = await get_default_help(language_for_reply)
            await connection_manager.send_text_message(account, user_help, order_data.orderNumber)

        except Exception as e:
            logger.error(f"Error handling order status 3 for BUY order: {str(e)}\n{traceback.format_exc()}")

    async def _handle_order_status_4_buy(
        self,
        connection_manager,
        account: str,
        conn,
        order_data: OrderData
    ) -> None:
        """Handle order status 4 (completion) for BUY orders - we are the buyer."""
        try:
            await self._generic_reply_buy(connection_manager, account, order_data, 4, conn)
            
            # For BUY orders, we don't need to do the same processing as SELL orders
            # since we're the ones receiving the crypto, not selling it
            logger.info(f"BUY order {order_data.orderNumber} completed successfully")

        except Exception as e:
            logger.error(f"Error handling order status 4 for BUY order: {str(e)}\n{traceback.format_exc()}")

    # ==========================================
    # GENERIC REPLY METHODS
    # ==========================================

    async def _generic_reply(
        self,
        connection_manager,
        account: str,
        order_data: OrderData,
        status_code: int,
        conn
    ) -> None:
        """Send generic reply based on status code and user's language preference for SELL orders."""
        try:
            # Get user's language preference
            user_language = await LanguageSelector.check_language_preference(conn, order_data.buyerName)
            
            # Fallback to determine_language if no preference set
            current_language = user_language or determine_language(order_data.fiatUnit)
            
            messages_to_send = await get_message_by_language(
                current_language,
                status_code,
                order_data.buyerName
            )
            
            if messages_to_send is None:
                logger.warning(
                    f"No messages found - Language: {current_language}, "
                    f"Status: {status_code}, Buyer: {order_data.buyerName}"
                )
                return

            await send_messages(
                connection_manager,
                account,
                order_data.orderNumber,
                messages_to_send
            )

        except Exception as e:
            logger.error(f"Error sending generic reply: {str(e)}\n{traceback.format_exc()}")

    async def _generic_reply_buy(
        self,
        connection_manager,
        account: str,
        order_data: OrderData,
        status_code: int,
        conn
    ) -> None:
        """Send generic reply based on status code for BUY orders - customer is the seller."""
        try:
            # For BUY orders, use determine_language since we don't store seller preferences
            current_language = determine_language(order_data.fiatUnit)
            
            messages_to_send = await get_message_by_language(
                current_language,
                status_code,
                order_data.sellerName  # Use sellerName since customer is the seller
            )
            
            if messages_to_send is None:
                logger.warning(
                    f"No messages found - Language: {current_language}, "
                    f"Status: {status_code}, Seller: {order_data.sellerName}"
                )
                return

            await send_messages(
                connection_manager,
                account,
                order_data.orderNumber,
                messages_to_send
            )

        except Exception as e:
            logger.error(f"Error sending generic reply for BUY order: {str(e)}\n{traceback.format_exc()}")

    # ==========================================
    # TEXT MESSAGE HANDLING
    # ==========================================

    async def handle_text_message(
        self,
        connection_manager,
        account: str,
        content: str,
        order_data: OrderData,
        conn
    ) -> None:
        """Handle text messages."""
        try:
            logger.info(f"Order status: {order_data.orderStatus}, Trade type: {order_data.tradeType}")

            if order_data.orderStatus not in [1, 2]:
                return

            # Handle BUY orders differently - we are the buyer, customer is the seller
            if order_data.tradeType == 'BUY':
                await self.process_buy_order_text(
                    order_data,
                    conn,
                    connection_manager,
                    account,
                    content
                )
            else:
                # Original SELL logic - we are the seller, customer is the buyer
                await self.process_customer_verification(
                    order_data,
                    conn,
                    connection_manager,
                    account,
                    content
                )

        except Exception as e:
            logger.error(f"Text message handling error: {str(e)}\n{traceback.format_exc()}")

    async def process_buy_order_text(
        self,
        order_data: OrderData,
        conn,
        connection_manager,
        account: str,
        content: str
    ) -> None:
        """Handle text messages for BUY orders - simplified flow since customer is the seller."""
        try:
            logger.info(f"Processing BUY order text for {order_data.orderNumber}")
            
            # For BUY orders, we only handle help requests and menu responses
            if content in ['ayuda', 'help']:
                if not await is_menu_presented(conn, order_data.orderNumber):
                    await self.present_menu_based_on_status_buy(
                        connection_manager,
                        account,
                        order_data,
                        conn
                    )
            elif content.isdigit():
                await self.handle_menu_response_buy(
                    connection_manager,
                    account,
                    int(content),
                    order_data,
                    conn
                )
            
            # We ignore all other text for BUY orders - no verification flow

        except Exception as e:
            logger.error(
                f"BUY order text processing error - Order: {order_data.orderNumber}, "
                f"Error: {str(e)}\n{traceback.format_exc()}"
            )

    async def process_customer_verification(
        self,
        order_data: OrderData,
        conn,
        connection_manager,
        account: str,
        content: str
    ) -> None:
        """Handle customer verification process for SELL orders."""
        try:
            # First check if user is in language selection mode
            if await LanguageSelector.is_language_selection_pending(conn, order_data.buyerName):
                # User is selecting language
                language_selected, language_code = await LanguageSelector.process_language_selection(
                    conn, order_data.buyerName, content, connection_manager, account, order_data.orderNumber
                )
                
                if language_selected:
                    # Language now set, proceed to anti-fraud
                    anti_fraud_stage = await get_anti_fraud_stage(conn, order_data.buyerName) or 0
                    await self._generic_reply(connection_manager, account, order_data, 1, conn)
                    await handle_user_verification(
                        order_data.buyerName,
                        order_data.sellerName,
                        conn,
                        anti_fraud_stage,
                        "",  # Reset content since this was language selection
                        order_data.orderNumber,
                        connection_manager,
                        account,
                        self.payment_manager,
                        order_data.fiatUnit,
                        order_data.payType
                    )
                # If language not selected, we've already sent error message, wait for next response
                return

            # Check if user has language preference set - MANDATORY at this point
            user_language = await LanguageSelector.check_language_preference(conn, order_data.buyerName)
            if not user_language:
                # User somehow reached this stage without language selection - force it now
                logger.warning(f"User {order_data.buyerName} reached verification without language selection")
                
                # Initiate language selection immediately
                await LanguageSelector.initiate_language_selection(
                    conn, order_data.buyerName, connection_manager, account, order_data.orderNumber
                )
                return

            # At this point, user MUST have a language preference set
            logger.info(f"Processing verification for {order_data.buyerName} in language: {user_language}")

            # Normal verification flow
            kyc_status = await get_kyc_status(conn, order_data.buyerName)
            anti_fraud_stage = await get_anti_fraud_stage(conn, order_data.buyerName) or 0

            # Check if still in anti-fraud process (stages vary by flow type)
            max_stage = 3 if order_data.payType == 'OXXO' or order_data.fiatUnit == 'USD' else 4
            
            if kyc_status == 0 or anti_fraud_stage <= max_stage:
                await handle_user_verification(
                    order_data.buyerName,
                    order_data.sellerName,
                    conn,
                    anti_fraud_stage,
                    content,
                    order_data.orderNumber,
                    connection_manager,
                    account,
                    self.payment_manager,
                    order_data.fiatUnit,
                    order_data.payType
                )
                return

            # Handle returning customers
            returning_customer_stage = await get_returning_customer_stage(conn, order_data.orderNumber) or 0
            logger.info(f"Returning customer stage: {returning_customer_stage}")

            if returning_customer_stage < 3:
                buyer_bank = (
                    order_data.buyer_bank 
                    if order_data.buyer_bank is not None 
                    else await get_buyer_bank(conn, order_data.buyerName)
                )
                await returning_customer(
                        order_data.buyerName,
                        conn,
                        returning_customer_stage,
                        content,
                        order_data.orderNumber,
                        connection_manager,
                        account,
                        self.payment_manager,
                        buyer_bank,
                        order_data.fiatUnit,
                        order_data.payType
                    )

            elif content in ['ayuda', 'help']:
                if not await is_menu_presented(conn, order_data.orderNumber):
                    await self.present_menu_based_on_status(
                        connection_manager,
                        account,
                        order_data,
                        conn
                    )
            elif content.isdigit():
                await self.handle_menu_response(
                    connection_manager,
                    account,
                    int(content),
                    order_data,
                    conn
                )

        except Exception as e:
            logger.error(
                f"Customer verification error - Buyer: {order_data.buyerName}, "
                f"Error: {str(e)}\n{traceback.format_exc()}"
            )

    # ==========================================
    # IMAGE MESSAGE HANDLING
    # ==========================================

    async def handle_image_message(
            self,
            connection_manager,
            account: str,
            msg_json: Dict[str, Any],
            order_data: OrderData,
            conn
        ) -> None:
            """Handle image messages."""
            try:
                # For BUY orders, we ignore images completely
                if order_data.tradeType == 'BUY':
                    logger.info(f"Ignoring image for BUY order {order_data.orderNumber}")
                    return

                # Original SELL order image handling logic
                await self._generic_reply(connection_manager, account, order_data, 100, conn)

                if order_data.orderStatus == 1:
                    # Get user's language for the message
                    language = await LanguageSelector.check_language_preference(conn, order_data.buyerName)
                    
                    if language == 'en':
                        message = "Please mark the order as paid if you have already sent the payment."
                    else:
                        message = "Por favor marcar la orden como pagada si ya envio el pago."
                    
                    await connection_manager.send_text_message(
                        account,
                        message,
                        order_data.orderNumber
                    )

                # Validate image URL
                image_URL = msg_json.get('imageUrl')
                if not image_URL:
                    logger.error(f"No image URL provided for order {order_data.orderNumber}")
                    return

                # Get and validate buyer's bank
                buyer_bank = await get_buyer_bank(conn, order_data.buyerName)
                if not buyer_bank:
                    logger.error(f"No buyer bank found for {order_data.buyerName} in order {order_data.orderNumber}")
                    return

                # Get and validate seller's bank
                order_details = await get_order_details(conn, order_data.orderNumber)
                if not order_details:
                    logger.error(f"Could not fetch order details for order {order_data.orderNumber}")
                    return

                seller_bank = order_details.get('seller_bank')
                if not seller_bank:
                    logger.error(f"No seller bank found for order {order_data.orderNumber}")
                    return

                # Now we can safely use lower() as we've validated seller_bank is not None
                seller_bank = seller_bank.lower()

                # Use the validator's handle_bank_validation method
                if self.validator:
                    await self.validator.handle_bank_validation(
                        order_data,
                        buyer_bank,
                        seller_bank,
                        image_URL,
                        conn,
                        account,
                        order_data.buyerName
                    )
                else:
                    logger.error(f"Validator not initialized for order {order_data.orderNumber}")

            except Exception as e:
                logger.error(
                    f"Image message handling error for order {order_data.orderNumber} - "
                    f"Error: {str(e)}\n{traceback.format_exc()}"
                )


    # ==========================================
    # MENU HANDLING FOR SELL ORDERS
    # ==========================================

    async def present_menu_based_on_status(
        self,
        connection_manager,
        account: str,
        order_data: OrderData,
        conn
    ) -> None:
        """Present menu options based on order status and user's language preference for SELL orders."""
        try:
            # Get user's language preference
            language_for_menu = await LanguageSelector.check_language_preference(conn, order_data.buyerName)

            menu = await get_menu_for_order(
                language_for_menu,
                order_data.orderStatus
            )
            msg = '\n'.join(menu)
            await connection_manager.send_text_message(
                account,
                msg,
                order_data.orderNumber
            )
            await set_menu_presented(conn, order_data.orderNumber, True)
            logger.info(f"Menu presented for order {order_data.orderNumber} in language {language_for_menu}")

        except Exception as e:
            logger.error(f"Error presenting menu: {str(e)}\n{traceback.format_exc()}")

    async def handle_menu_response(
        self,
        connection_manager,
        account: str,
        choice: int,
        order_data: OrderData,
        conn
    ) -> None:
        """Handle customer's menu selection using their language preference for SELL orders."""
        try:
            # Get user's language preference
            language = await LanguageSelector.check_language_preference(conn, order_data.buyerName)
            
            if await is_valid_choice(language, order_data.orderStatus, choice):
                if choice == 1:
                    payment_details = await self.payment_manager.get_payment_details(
                        conn,
                        order_data.orderNumber,
                        order_data.buyerName
                    )
                    await connection_manager.send_text_message(
                        account,
                        payment_details,
                        order_data.orderNumber
                    )
                else:
                    response = await get_response_for_menu_choice(
                        language,
                        order_data.orderStatus,
                        choice,
                        order_data.buyerName
                    )
                    await connection_manager.send_text_message(
                        account,
                        response,
                        order_data.orderNumber
                    )
                logger.info(
                    f"Menu choice {choice} processed for order {order_data.orderNumber} in language {language}"
                )
            else:
                response = await get_invalid_choice_reply(language)
                await connection_manager.send_text_message(
                    account,
                    response,
                    order_data.orderNumber
                )
                logger.warning(
                    f"Invalid menu choice {choice} for order {order_data.orderNumber}"
                )

        except Exception as e:
            logger.error(
                f"Error handling menu response - Order: {order_data.orderNumber}, "
                f"Choice: {choice}, Error: {str(e)}\n{traceback.format_exc()}"
            )

    # ==========================================
    # MENU HANDLING FOR BUY ORDERS
    # ==========================================

    async def present_menu_based_on_status_buy(
        self,
        connection_manager,
        account: str,
        order_data: OrderData,
        conn
    ) -> None:
        """Present menu options for BUY orders - customer is the seller."""
        try:
            # For BUY orders, use determine_language since we don't store seller preferences
            language_for_menu = determine_language(order_data.fiatUnit)

            menu = await get_menu_for_order(
                language_for_menu,
                order_data.orderStatus
            )
            msg = '\n'.join(menu)
            await connection_manager.send_text_message(
                account,
                msg,
                order_data.orderNumber
            )
            await set_menu_presented(conn, order_data.orderNumber, True)
            logger.info(f"Menu presented for BUY order {order_data.orderNumber} in language {language_for_menu}")

        except Exception as e:
            logger.error(f"Error presenting menu for BUY order: {str(e)}\n{traceback.format_exc()}")

    async def handle_menu_response_buy(
        self,
        connection_manager,
        account: str,
        choice: int,
        order_data: OrderData,
        conn
    ) -> None:
        """Handle menu selection for BUY orders - customer is the seller."""
        try:
            # For BUY orders, use determine_language since we don't store seller preferences
            language = determine_language(order_data.fiatUnit)
            
            if await is_valid_choice(language, order_data.orderStatus, choice):
                if choice == 1:
                    payment_details = await self.payment_manager.get_payment_details(
                        conn,
                        order_data.orderNumber,
                        order_data.sellerName  # Use sellerName since customer is the seller
                    )
                    await connection_manager.send_text_message(
                        account,
                        payment_details,
                        order_data.orderNumber
                    )
                else:
                    response = await get_response_for_menu_choice(
                        language,
                        order_data.orderStatus,
                        choice,
                        order_data.sellerName  # Use sellerName since customer is the seller
                    )
                    await connection_manager.send_text_message(
                        account,
                        response,
                        order_data.orderNumber
                    )
                logger.info(
                    f"Menu choice {choice} processed for BUY order {order_data.orderNumber} in language {language}"
                )
            else:
                response = await get_invalid_choice_reply(language)
                await connection_manager.send_text_message(
                    account,
                    response,
                    order_data.orderNumber
                )
                logger.warning(
                    f"Invalid menu choice {choice} for BUY order {order_data.orderNumber}"
                )

        except Exception as e:
            logger.error(
                f"Error handling menu response for BUY order - Order: {order_data.orderNumber}, "
                f"Choice: {choice}, Error: {str(e)}\n{traceback.format_exc()}"
            )