# bpa/binance_returning_customer.py
import asyncio
import unicodedata
import traceback
from typing import Optional, List

from data.cache.order_cache import OrderCache
from trading.p2p.kyc.blacklist import add_to_blacklist
from trading.p2p.kyc.binance_language_selection import LanguageSelector
from localization.lang_utils import (
    get_anti_fraud_stage3, get_anti_fraud_not_valid_response, 
    get_anti_fraud_user_denied, get_customer_verification_messages
)
from utils.common_vars import NOT_ACCEPTED_BANKS, ACCEPTED_BANKS, normalize_bank_name
from data.database.operations.binance_db_set import update_buyer_bank, update_returning_customer_stage
from utils.common_utils import send_messages
from utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

def normalize_string(input_str: str) -> str:
    """Normalize string by removing diacritics and converting to lowercase."""
    if not input_str:
        return ""
    try:
        normalized_str = unicodedata.normalize('NFD', input_str)
        return ''.join([c for c in normalized_str if unicodedata.category(c) != 'Mn']).lower()
    except Exception as e:
        logger.error(f"Error normalizing string: {str(e)}")
        return ""

def get_valid_yes_no_responses(language: str) -> list:
    """Get valid yes/no responses for the specified language."""
    if language == 'en':
        return ['yes', 'no', 'y', 'n', 'yes.', 'no.']
    else:  # Spanish
        return ['si', 'no', 'n', 'no ', 'no.', 'sí']

def get_yes_responses(language: str) -> list:
    """Get 'yes' responses for the specified language."""
    if language == 'en':
        return ['yes', 'y']
    else:  # Spanish
        return ['si', 'sí']

def get_no_responses(language: str) -> list:
    """Get 'no' responses for the specified language."""
    return ['no', 'n']  # Same in both languages

async def update_stage_with_cache(conn, orderNumber, stage):
    """Update the returning customer stage in both cache and database."""
    await OrderCache.update_fields(orderNumber, {'returning_customer_stage': stage})
    await update_returning_customer_stage(conn, orderNumber, stage)

async def handle_bank_verification(
    conn,
    normalized_response: str,
    buyerName: str,
    account: str,
    orderNumber: str,
    connection_manager,
    questions: List[str],
    returning_customer_stage: int,
    language: str = 'es'
) -> Optional[str]:
    """Handle the bank verification process for both new and returning customers."""
    try:
        if not normalized_response:
            logger.warning(f"Empty bank name provided for buyer {buyerName}")
            return None

        standard_bank_name = normalize_bank_name(normalized_response)
        
        if standard_bank_name in [normalize_bank_name(bank) for bank in NOT_ACCEPTED_BANKS]:
            stage3_message = get_anti_fraud_stage3(language)
            await connection_manager.send_text_message(account, stage3_message, orderNumber)
            await add_to_blacklist(conn, buyerName, orderNumber, None, standard_bank_name, returning_customer_stage)
            logger.info(f"Bank {standard_bank_name} is not accepted for buyer {buyerName}")
            return None

        if standard_bank_name in [normalize_bank_name(bank) for bank in ACCEPTED_BANKS]:
            await OrderCache.update_fields(orderNumber, {'buyer_bank': standard_bank_name})
            await update_buyer_bank(conn, buyerName, standard_bank_name)
            logger.info(f"Bank {standard_bank_name} verified successfully for buyer {buyerName}")
            return standard_bank_name
        
        # Get localized verification messages
        verification_messages = get_customer_verification_messages(language)
        accepted_banks_list = ', '.join(ACCEPTED_BANKS)
        bank_fail_message = verification_messages["bank_verification_failed"](accepted_banks_list)
        
        await connection_manager.send_text_message(account, bank_fail_message, orderNumber)
        await asyncio.sleep(2)
        
        current_question = questions[returning_customer_stage]
        await connection_manager.send_text_message(account, current_question, orderNumber)
        logger.warning(f"Invalid bank {standard_bank_name} provided by buyer {buyerName}")
        return None

    except Exception as e:
        logger.error(f"Error in bank verification for buyer {buyerName}: {str(e)}\n{traceback.format_exc()}")
        return None

async def handle_invalid_response(
    connection_manager,
    account: str,
    orderNumber: str,
    questions: List[str],
    returning_customer_stage: int,
    language: str = 'es'
) -> None:
    """Handle invalid yes/no responses."""
    try:
        invalid_response_message = get_anti_fraud_not_valid_response(language)
        await connection_manager.send_text_message(account, invalid_response_message, orderNumber)
        await asyncio.sleep(2)
        await connection_manager.send_text_message(account, questions[returning_customer_stage], orderNumber)
    except Exception as e:
        logger.error(f"Error handling invalid response for order {orderNumber}: {str(e)}")

async def handle_customer_denial(
    conn,
    buyerName: str,
    orderNumber: str,
    normalized_response: str,
    returning_customer_stage: int,
    connection_manager,
    account: str,
    language: str = 'es'
) -> None:
    """Handle cases where the customer is denied."""
    try:
        denied_message = get_anti_fraud_user_denied(language)
        await connection_manager.send_text_message(account, denied_message, orderNumber)
        await add_to_blacklist(conn, buyerName, orderNumber, None, normalized_response, returning_customer_stage)
        logger.info(f"Customer {buyerName} denied for order {orderNumber}")
    except Exception as e:
        logger.error(f"Error handling customer denial for buyer {buyerName}: {str(e)}")

def get_customer_questions(
    buyerName: str,
    buyer_bank: Optional[str],
    fiatUnit: str = 'MXN',
    payType: str = None,
    language: str = 'es'
) -> List[str]:
    """Generate verification questions based on customer context and language."""
    try:
        # Get localized verification messages
        verification_messages = get_customer_verification_messages(language)
        
        if payType == 'OXXO':
            if language == 'en':
                return ["For the OXXO payment method, are you making the payment in cash?"]
            else:
                return ["Para el método de pago OXXO, ¿está realizando el pago en efectivo?"]
        
        if fiatUnit == 'USD':
            payment_method_names = {
                'SkrillMoneybookers': 'Skrill',
                'BANK': 'Wise' if language == 'en' else 'wise',
                'Zelle': 'Zelle',
                'PayPal': 'PayPal',
                'CashApp': 'Cash App',
                'Venmo': 'Venmo'
            }
            method_name = payment_method_names.get(payType, 'payment method' if language == 'en' else 'método de pago')
            
            if language == 'en':
                ownership_question = (
                    f"To confirm your identity, please confirm that the name on your {method_name} account "
                    f"is: {buyerName}. Reply 'YES' to confirm or 'NO' if it's different."
                )
            else:
                ownership_question = (
                    f"Para confirmar tu identidad, confirma que el nombre en tu cuenta de {method_name} "
                    f"es: {buyerName}. Responde 'SI' para confirmar o 'NO' si es diferente."
                )
            return [ownership_question]
        
        # MXN flow
        return [
            verification_messages["bank_confirmation"](buyer_bank) if buyer_bank else "",
            verification_messages["bank_request"],
            verification_messages["account_ownership"](buyerName)
        ]
    except Exception as e:
        logger.error(f"Error generating questions for buyer {buyerName}: {str(e)}")
        return []

async def returning_customer(
    buyerName: str, conn, returning_customer_stage: int, response: str, orderNumber: str,
    connection_manager, account, payment_manager, buyer_bank: Optional[str] = None,
    fiatUnit: str = 'MXN', payType: str = None 
) -> None:
    """Verify returning customer's bank information and provide payment details if valid."""
    try:
        # Get user's language preference
        language = await LanguageSelector.check_language_preference(conn, buyerName)
        
        logger.info(f"Processing returning customer {buyerName} in language: {language}, stage: {returning_customer_stage}, response: {response}, order: {orderNumber}, account: {account}, bank: {buyer_bank}")

        questions = get_customer_questions(buyerName, buyer_bank, fiatUnit, payType, language)
        normalized_response = normalize_string(response.strip())
        
        if returning_customer_stage >= len(questions):
            logger.info(f'Returning customer stage {returning_customer_stage}, length is {len(questions)}')
            return

        if not normalized_response:
            await connection_manager.send_text_message(account, questions[returning_customer_stage], orderNumber)
            return

        # Get valid responses for this language
        valid_yes_no = get_valid_yes_no_responses(language)
        yes_responses = get_yes_responses(language)
        no_responses = get_no_responses(language)

        # Single-step flows for OXXO and USD
        if payType == 'OXXO' or fiatUnit == 'USD':
            if returning_customer_stage == 0:
                if normalized_response not in valid_yes_no:
                    await handle_invalid_response(connection_manager, account, orderNumber, questions, returning_customer_stage, language)
                    return
                
                if normalized_response in no_responses:
                    await handle_customer_denial(conn, buyerName, orderNumber, normalized_response, 0, connection_manager, account, language)
                    return
                
                payment_details = await payment_manager.get_payment_details(conn, orderNumber, buyerName)
                await send_messages(connection_manager, account, orderNumber, [payment_details])
                await update_stage_with_cache(conn, orderNumber, 3)  # Mark as complete
                return
            
        # MXN Bank Transfer Flow (multi-step)
        # Stage 0: Confirm existing bank
        if returning_customer_stage == 0:
            if normalized_response not in valid_yes_no:
                await handle_invalid_response(connection_manager, account, orderNumber, questions, 0, language)
                return

            if normalized_response in yes_responses:
                # User confirmed same bank, skip to account ownership (stage 2)
                next_stage = 2
                await update_stage_with_cache(conn, orderNumber, next_stage)
                await connection_manager.send_text_message(account, questions[next_stage], orderNumber)
                return
            else:  # 'no'
                # Need new bank, move to bank request (stage 1)
                next_stage = 1
                await update_stage_with_cache(conn, orderNumber, next_stage)
                await connection_manager.send_text_message(account, questions[next_stage], orderNumber)
                return

        # Stage 1: Get and verify new bank
        if returning_customer_stage == 1:
            verified_bank = await handle_bank_verification(
                conn, normalized_response, buyerName, account, orderNumber, 
                connection_manager, questions, 1, language
            )
            if not verified_bank:
                return

            # Bank verified, move to account ownership (stage 2)
            next_stage = 2
            await update_stage_with_cache(conn, orderNumber, next_stage)
            await connection_manager.send_text_message(account, questions[next_stage], orderNumber)
            return

        # Stage 2: Confirm account ownership
        if returning_customer_stage == 2:
            if normalized_response not in valid_yes_no:
                await handle_invalid_response(connection_manager, account, orderNumber, questions, 2, language)
                return

            if normalized_response in no_responses:
                await handle_customer_denial(conn, buyerName, orderNumber, normalized_response, 2, connection_manager, account, language)
                return

            # All checks passed, provide payment details and complete
            payment_details = await payment_manager.get_payment_details(conn, orderNumber, buyerName)
            if payment_details.get('account_number'):
                await OrderCache.update_fields(orderNumber, {
                    'account_number': payment_details['account_number'],
                    'seller_bank': payment_details.get('bank_name')
                })
            await send_messages(connection_manager, account, orderNumber, [payment_details])
            
            await update_stage_with_cache(conn, orderNumber, 3)  # Mark as complete
            logger.info(f"Completed returning customer flow for buyer {buyerName} in language {language}")

    except Exception as e:
        logger.error(f"Error in returning customer flow for buyer {buyerName}: {str(e)}\n{traceback.format_exc()}")