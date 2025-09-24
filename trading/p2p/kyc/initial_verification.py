# anti_fraud_system.py
"""
Anti-Fraud Verification System for P2P Cryptocurrency Trading

Implements multi-stage verification process to prevent fraud in cryptocurrency
transactions across different payment methods and currencies.

Verification Flows:
- MXN (Bank): Employment → Pressure → Refund → Bank → Ownership verification
- USD (Digital): Employment → Pressure → Refund → Account ownership verification  
- OXXO (Cash): Employment → Pressure → Refund → Cash payment verification
"""

import asyncio
import string
import unicodedata
import traceback
from typing import List, Optional, Dict, Any
from enum import Enum

from data.cache.order_cache import OrderCache
from trading.p2p.kyc.blacklist import add_to_blacklist
from data.database.operations.binance_db_set import update_anti_fraud_stage, update_buyer_bank, update_kyc_status, update_order_details
from data.database.operations.binance_db_get import get_order_details
from trading.p2p.kyc.binance_language_selection import LanguageSelector
from localization.lang_utils import (
    payment_warning_mxn, payment_warning_usd,
    get_anti_fraud_messages, get_anti_fraud_not_valid_response,
    get_anti_fraud_possible_fraud, get_anti_fraud_user_denied,
    get_anti_fraud_stage3
)
from utils.common_vars import NOT_ACCEPTED_BANKS, ACCEPTED_BANKS, normalize_bank_name
from utils.common_utils import send_messages
from utils.logging_config import setup_logging

logger = setup_logging(log_filename='balance_manager.log')


class VerificationFlow(Enum):
    """Supported verification flows based on payment method"""
    MXN_BANK = "mxn_bank"
    USD_DIGITAL = "usd_digital" 
    OXXO_CASH = "oxxo_cash"


class VerificationStage(Enum):
    """Verification stages with clear progression"""
    EMPLOYMENT = 0
    PRESSURE = 1
    REFUND = 2
    PAYMENT_METHOD = 3  # Bank/Account/OXXO verification
    OWNERSHIP = 4       # Account ownership (MXN only)


class FraudVerificationSystem:
    """
    Handles multi-stage anti-fraud verification for different payment flows.
    
    Manages user verification through progressive stages with language support
    and flow-specific business logic.
    """
    
    @staticmethod
    def normalize_string(input_str: str) -> str:
        """Normalize string by removing diacritics and punctuation"""
        normalized = unicodedata.normalize('NFD', input_str)
        stripped = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
        return stripped.translate(str.maketrans('', '', string.punctuation)).lower()
    
    @staticmethod
    def determine_verification_flow(fiat_unit: str, pay_type: str) -> VerificationFlow:
        """Determine which verification flow to use"""
        if pay_type == 'OXXO':
            return VerificationFlow.OXXO_CASH
        elif fiat_unit == 'USD':
            return VerificationFlow.USD_DIGITAL
        else:
            return VerificationFlow.MXN_BANK
    
    @staticmethod
    def get_verification_questions(
        buyer_name: str,
        order_no: str,
        flow: VerificationFlow,
        language: str = 'es'
    ) -> List[str]:
        """Generate verification questions based on flow and language"""
        anti_fraud_messages = get_anti_fraud_messages(language)
        
        # Base questions for all flows
        base_questions = [
            anti_fraud_messages["employment_check"],
            anti_fraud_messages["pressure_check"],
            anti_fraud_messages["refund_agreement"](order_no)
        ]
        
        # Add flow-specific questions
        if flow == VerificationFlow.OXXO_CASH:
            return base_questions + [anti_fraud_messages["oxxo_cash_payment"]]
        
        elif flow == VerificationFlow.USD_DIGITAL:
            ownership_msg = (
                f"To confirm your identity, please confirm that the account name "
                f"matches: {buyer_name}. Reply 'YES' to confirm or 'NO' if different."
                if language == 'en' else
                f"Para confirmar tu identidad, confirma que el nombre de la cuenta "
                f"es: {buyer_name}. Responde 'SI' para confirmar o 'NO' si es diferente."
            )
            return base_questions + [ownership_msg]
        
        else:  # MXN_BANK
            return base_questions + [
                anti_fraud_messages["bank_request"],
                anti_fraud_messages["account_ownership"](buyer_name)
            ]
    
    @staticmethod
    def get_response_validators(language: str) -> Dict[str, List[str]]:
        """Get valid response patterns for language"""
        if language == 'en':
            return {
                'valid_responses': ['yes', 'no', 'y', 'n'],
                'yes_responses': ['yes', 'y'],
                'no_responses': ['no', 'n']
            }
        else:  # Spanish
            return {
                'valid_responses': ['si', 'no', 'sí', 'n'],
                'yes_responses': ['si', 'sí'],
                'no_responses': ['no', 'n']
            }


class VerificationProcessor:
    """Processes verification responses and manages state transitions"""
    
    def __init__(self, conn, connection_manager, payment_manager):
        self.conn = conn
        self.connection_manager = connection_manager
        self.payment_manager = payment_manager
    
    async def get_order_data(self, order_no: str) -> Optional[Dict[str, Any]]:
        """Get order data from cache or database"""
        order_data = await OrderCache.get_order(order_no)
        
        if not order_data:
            order_data = await get_order_details(self.conn, order_no)
            if order_data:
                await OrderCache.set_order(order_no, order_data)
        
        return order_data
    
    async def update_verification_field(self, order_no: str, buyer_name: str, field: str, value: Any):
        """Update field in cache and database"""
        await OrderCache.update_fields(order_no, {field: value})
        
        if field == 'anti_fraud_stage':
            await update_anti_fraud_stage(self.conn, buyer_name, value)
        elif field == 'buyer_bank':
            await update_buyer_bank(self.conn, buyer_name, value)
        elif field == 'kyc_status':
            await update_kyc_status(self.conn, buyer_name, value)
    
    async def handle_fraud_detection(
        self,
        buyer_name: str,
        order_no: str,
        account: str,
        response: str,
        stage: int,
        language: str
    ) -> bool:
        """Handle fraud detection and blacklisting"""
        fraud_message = get_anti_fraud_possible_fraud(language)
        await self.connection_manager.send_text_message(account, fraud_message, order_no)
        await add_to_blacklist(self.conn, buyer_name, order_no, None, response, stage)
        return True
    
    async def handle_bank_verification(
        self,
        response: str,
        buyer_name: str,
        order_no: str,
        account: str,
        questions: List[str],
        language: str
    ) -> Optional[str]:
        """Process bank verification step"""
        try:
            normalized_bank = FraudVerificationSystem.normalize_string(response)
            standard_bank_name = normalize_bank_name(response)
            
            # Check blacklisted banks
            if standard_bank_name in [normalize_bank_name(bank) for bank in NOT_ACCEPTED_BANKS]:
                stage3_message = get_anti_fraud_stage3(language)
                await self.connection_manager.send_text_message(account, stage3_message, order_no)
                await add_to_blacklist(self.conn, buyer_name, order_no, None, standard_bank_name, 3)
                return None
            
            # Check accepted banks
            if standard_bank_name in [normalize_bank_name(bank) for bank in ACCEPTED_BANKS]:
                await self.update_verification_field(order_no, buyer_name, 'buyer_bank', standard_bank_name)
                return standard_bank_name
            
            # Invalid bank - request retry
            accepted_banks_list = ', '.join(ACCEPTED_BANKS)
            anti_fraud_messages = get_anti_fraud_messages(language)
            fail_message = anti_fraud_messages["bank_verification_failed"](accepted_banks_list)
            
            await self.connection_manager.send_text_message(account, fail_message, order_no)
            await asyncio.sleep(2)
            await self.connection_manager.send_text_message(account, questions[3], order_no)
            return None
            
        except Exception as e:
            logger.error(f"Bank verification error for {buyer_name}: {e}")
            return None
    
    async def send_invalid_response_message(
        self,
        account: str,
        order_no: str,
        questions: List[str],
        stage: int,
        language: str
    ):
        """Send invalid response message and retry question"""
        invalid_message = get_anti_fraud_not_valid_response(language)
        await self.connection_manager.send_text_message(account, invalid_message, order_no)
        await asyncio.sleep(2)
        await self.connection_manager.send_text_message(account, questions[stage], order_no)
    
    async def complete_verification(
        self,
        buyer_name: str,
        order_no: str,
        account: str,
        fiat_unit: str
    ):
        """Complete verification and send payment details"""
        # Mark KYC as complete
        await self.update_verification_field(order_no, buyer_name, 'kyc_status', 1)
        
        # Get payment details
        payment_details = await self.payment_manager.get_payment_details(
            self.conn, order_no, buyer_name
        )
        
        # Update cache and database with payment info
        if payment_details.get('account_number'):
            cache_updates = {
                'account_number': payment_details['account_number'],
                'seller_bank': payment_details.get('bank_name')
            }
            await OrderCache.update_fields(order_no, cache_updates)
            
            await update_order_details(
                self.conn,
                order_no,
                payment_details['account_number'],
                payment_details.get('bank_name')
            )
        
        # Send appropriate payment warning and details
        payment_warning = payment_warning_usd if fiat_unit == 'USD' else payment_warning_mxn
        messages = [payment_warning, payment_details]
        await send_messages(self.connection_manager, account, order_no, messages)


async def handle_user_verification(
    buyer_name: str,
    seller_name: str,
    conn,
    anti_fraud_stage: int,
    response: str,
    order_no: str,
    connection_manager,
    account: str,
    payment_manager,
    fiat_unit: str = 'MXN',
    pay_type: str = None
) -> None:
    """
    Main entry point for anti-fraud verification process.
    
    Handles multi-stage verification with support for different payment flows
    and languages. Manages state progression and fraud detection.
    """
    try:
        # Initialize processor
        processor = VerificationProcessor(conn, connection_manager, payment_manager)
        
        # Get user language preference
        language = await LanguageSelector.check_language_preference(conn, buyer_name)
        logger.info(f"Processing verification for {buyer_name} (stage: {anti_fraud_stage}, lang: {language})")
        
        # Get order data
        order_data = await processor.get_order_data(order_no)
        if not order_data:
            logger.error(f"Order {order_no} not found")
            return
        
        # Determine verification flow and questions
        flow = FraudVerificationSystem.determine_verification_flow(fiat_unit, pay_type)
        questions = FraudVerificationSystem.get_verification_questions(
            buyer_name, order_no, flow, language
        )
        
        # Get response validators
        validators = FraudVerificationSystem.get_response_validators(language)
        normalized_response = FraudVerificationSystem.normalize_string(response.strip())
        
        # Handle initial empty response
        if anti_fraud_stage == 0 and not normalized_response:
            await connection_manager.send_text_message(account, questions[0], order_no)
            return
        
        # Validate stage bounds
        if anti_fraud_stage >= len(questions):
            logger.error(f"Invalid verification stage: {anti_fraud_stage}")
            return
        
        # Process stage-specific logic
        if anti_fraud_stage in [VerificationStage.EMPLOYMENT.value, VerificationStage.PRESSURE.value]:
            # Employment and pressure checks - "yes" indicates fraud
            if normalized_response not in validators['valid_responses']:
                await processor.send_invalid_response_message(
                    account, order_no, questions, anti_fraud_stage, language
                )
                return
            
            if normalized_response in validators['yes_responses']:
                await processor.handle_fraud_detection(
                    buyer_name, order_no, account, normalized_response, anti_fraud_stage, language
                )
                return
        
        elif anti_fraud_stage == VerificationStage.REFUND.value:
            # Refund agreement - "no" indicates non-compliance
            if normalized_response not in validators['valid_responses']:
                await processor.send_invalid_response_message(
                    account, order_no, questions, anti_fraud_stage, language
                )
                return
            
            if normalized_response in validators['no_responses']:
                denied_message = get_anti_fraud_user_denied(language)
                await connection_manager.send_text_message(account, denied_message, order_no)
                await add_to_blacklist(conn, buyer_name, order_no, None, normalized_response, anti_fraud_stage)
                return
        
        elif anti_fraud_stage == VerificationStage.PAYMENT_METHOD.value:
            # Handle flow-specific payment method verification
            if flow == VerificationFlow.MXN_BANK:
                # Bank verification for MXN
                verified_bank = await processor.handle_bank_verification(
                    response, buyer_name, order_no, account, questions, language
                )
                if not verified_bank:
                    return
                
                # Progress to ownership verification
                anti_fraud_stage = VerificationStage.OWNERSHIP.value
                await processor.update_verification_field(order_no, buyer_name, 'anti_fraud_stage', anti_fraud_stage)
                await connection_manager.send_text_message(account, questions[anti_fraud_stage], order_no)
                return
            
            else:
                # Account ownership or OXXO cash verification (yes/no)
                if normalized_response not in validators['valid_responses']:
                    await processor.send_invalid_response_message(
                        account, order_no, questions, anti_fraud_stage, language
                    )
                    return
                
                if normalized_response in validators['no_responses']:
                    # Failed verification
                    if flow == VerificationFlow.OXXO_CASH:
                        await processor.handle_fraud_detection(
                            buyer_name, order_no, account, "no_cash_payment", anti_fraud_stage, language
                        )
                    else:  # USD flow
                        await processor.handle_fraud_detection(
                            buyer_name, order_no, account, "name_mismatch", anti_fraud_stage, language
                        )
                    return
        
        elif anti_fraud_stage == VerificationStage.OWNERSHIP.value:
            # Final ownership verification for MXN flow
            if normalized_response not in validators['valid_responses']:
                await processor.send_invalid_response_message(
                    account, order_no, questions, anti_fraud_stage, language
                )
                return
            
            if normalized_response in validators['no_responses']:
                denied_message = get_anti_fraud_user_denied(language)
                await connection_manager.send_text_message(account, denied_message, order_no)
                await add_to_blacklist(conn, buyer_name, order_no, None, normalized_response, anti_fraud_stage)
                return
        
        # Progress to next stage
        anti_fraud_stage += 1
        await processor.update_verification_field(order_no, buyer_name, 'anti_fraud_stage', anti_fraud_stage)
        
        # Check if verification is complete
        if anti_fraud_stage >= len(questions):
            await processor.complete_verification(buyer_name, order_no, account, fiat_unit)
        else:
            # Send next question
            await connection_manager.send_text_message(account, questions[anti_fraud_stage], order_no)
    
    except Exception as e:
        logger.error(f"Verification error for {buyer_name}: {e}\n{traceback.format_exc()}")


# Convenience functions for backward compatibility
async def get_or_fetch_order_data(conn, order_no: str) -> Optional[Dict[str, Any]]:
    """Get order data from cache or database"""
    processor = VerificationProcessor(conn, None, None)
    return await processor.get_order_data(order_no)