# bpa/binance_SPEI_validation.py
"""
Transfer validation module that handles:
1. Queue-based transfer validation with retry logic
2. Bank receipt OCR processing for extracting tracking codes
3. CEP transfer validation via API calls
"""

import asyncio
import pytesseract
import re
import traceback
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from typing import List, Optional
from abc import ABC, abstractmethod

from cep import Transferencia
from src.utils.common_utils import download_image
from src.customer_service.kyc.language_selection import LanguageSelector
from src.utils.common_vars import BANK_SPEI_CODES
import logging
from src.utils.logging_config import setup_logging

setup_logging(log_filename='binance_main.log')
logger = logging.getLogger(__name__)

# ==========================================
# CEP VALIDATION FUNCTIONS
# ==========================================

async def validate_transfer(fecha, clave_rastreo, emisor, receptor, cuenta, monto):
    """Validate transfer using CEP API"""
    if isinstance(fecha, str):
        fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
    
    try:
        # Validate the transfer
        tr = await asyncio.to_thread(Transferencia.validar,
            fecha=fecha,
            clave_rastreo=clave_rastreo,
            emisor=emisor,
            receptor=receptor,
            cuenta=cuenta,
            monto=monto,
        )
        
        if tr is not None:
            # Log successful validation without downloading the PDF
            logger.info(f"Transfer validated successfully for clave: {clave_rastreo}")
            return True
        else:
            # Log failure if transfer could not be validated
            logger.info(f"Transfer validation failed for clave: {clave_rastreo}")
            return False
    except Exception as e:
        # Log the exception for better traceability
        logger.error(f"Error during transfer validation for clave {clave_rastreo}: {e}")
        return False

async def retry_request(func, retries=3, delay=1, backoff=2):
    """Retry a function call with exponential backoff"""
    for attempt in range(retries):
        try:
            result = await asyncio.to_thread(func)
            return result
        except Exception as e:
            if attempt == retries - 1:
                logger.error(f"Final attempt failed: {e}")
                raise
            
            wait_time = delay * (backoff ** attempt)
            logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    
    return None

# ==========================================
# BANK RECEIPT HANDLERS
# ==========================================

class BankReceiptHandler(ABC):
    """Abstract base class for bank receipt handlers"""
    
    @abstractmethod
    def extract_clave_de_rastreo(self, image):
        """Extract tracking number from image"""
        pass
    
    @abstractmethod
    def validate_clave_format(self, clave):
        """Validate the format of tracking number"""
        pass

class BBVAReceiptHandler(BankReceiptHandler):
    def extract_clave_de_rastreo(self, image):        
        custom_config = r'--oem 3 --psm 6'
        logger.info(f"Using Tesseract config: {custom_config}")

        raw_text = pytesseract.image_to_string(image, config=custom_config)
        logger.info(f"raw OCR text:\n{raw_text}")
        
        # Log each line separately for better analysis
        logger.info("OCR text by lines:")
        for i, line in enumerate(raw_text.split('\n')):
            logger.info(f"Line {i+1}: {repr(line)}")
        
        # Look for text containing "Clave" and log the search process
        lines = raw_text.split('\n')
        clave_text = None
        for i, line in enumerate(lines):
            if 'lave' in line.lower() and 'rastreo' in line.lower():
                logger.info(f"Found potential clave line at index {i}: {repr(line)}")
                if i + 1 < len(lines):
                    next_line = lines[i+1].strip()
                    logger.info(f"Next line: {repr(next_line)}")
                    if next_line.startswith('MBAN') or next_line.startswith('BNET'):
                        cleaned = next_line.upper().replace('O', '0').replace('I', '1')
                        if self.validate_clave_format(cleaned):
                            logger.info(f"Valid clave found: {cleaned}")
                            return cleaned
                    clave_text = line + next_line
                break
        
        # If not found directly after "Clave de rastreo", try cleaning full text
        logger.info("Attempting fallback search in full text...")
        cleaned_text = raw_text.upper()
        cleaned_text = cleaned_text.replace('O', '0').replace('I', '1')
        cleaned_text = cleaned_text.replace(' ', '')
        
        # Look for both MBAN and BNET patterns
        mban_matches = re.findall(r'MBAN[A-Z0-9]{20}', cleaned_text)
        bnet_matches = re.findall(r'BNET[A-Z0-9]{20}', cleaned_text)
        matches = mban_matches + bnet_matches
        
        logger.info(f"Fallback matches - MBAN: {mban_matches}, BNET: {bnet_matches}")
        
        if matches:
            clave = matches[0]
            if len(clave) == 24:
                if clave.startswith('MBAN'):
                    clave = 'MBAN01' + clave[6:]
                elif clave.startswith('BNET'):
                    clave = 'BNET01' + clave[6:]
                logger.info(f"Final clave from fallback: {clave}")
                return clave
                
        logger.info("No valid clave found in any attempt")
        return None

    def validate_clave_format(self, clave):
        if not clave or len(clave) != 24:
            return False
        # Allow both MBAN and BNET formats
        return bool(re.match(r'^(MBAN|BNET)[A-Za-z0-9]{20}$', clave))

class NUReceiptHandler(BankReceiptHandler):
    def extract_clave_de_rastreo(self, image):
        custom_config = r'--oem 3 --psm 6 -c tessedit_char_whitelist=NUJABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        text = pytesseract.image_to_string(image, config=custom_config)
        matches = re.findall(r'NU[A-Z0-9]{26}', text)
        
        if matches:
            clave = matches[0]
            if self.validate_clave_format(clave):
                return clave
        return None

    def validate_clave_format(self, clave):
        if not clave or len(clave) != 28:
            return False
        return bool(re.match(r'^NU[A-Z0-9]{26}$', clave))

class BanorteReceiptHandler(BankReceiptHandler):
    def extract_clave_de_rastreo(self, image):
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_config)
        matches = re.findall(r'[A-Za-z0-9]*CP0[A-Za-z0-9]{2,26}', text)
        
        if matches:
            clave = matches[0]
            if self.validate_clave_format(clave):
                return clave
        return None

    def validate_clave_format(self, clave):
        if not clave:
            return False
        return bool(re.match(r'^.*CP0[A-Z0-9]{2,26}$', clave))

def get_bank_handler(bank):
    """Factory function to get the appropriate bank handler"""
    handlers = {
        "BBVA": BBVAReceiptHandler,
        "NU": NUReceiptHandler,
        "BANORTE": BanorteReceiptHandler
    }
    handler_class = handlers.get(bank)
    if handler_class:
        return handler_class()
    raise ValueError(f"No handler available for bank: {bank}")

async def extract_clave_de_rastreo(image_url, bank):
    """Extract tracking code from bank receipt image"""
    img = await download_image(image_url)
    if not img:
        logger.error("Failed to download image")
        return None

    try:
        handler = get_bank_handler(bank)
        logger.info(f"Processing image for bank: {bank}")
        
        clave = handler.extract_clave_de_rastreo(img)
        if clave:
            logger.info(f"Extracted clave using {bank} handler: {clave}")
            return clave
            
        logger.info(f"No clave found for {bank}")
        return None
        
    except ValueError as e:
        logger.warning(f"Bank handler error: {e}")
    except Exception as e:
        logger.error(f"Error processing with bank handler: {e}", exc_info=True)
    
    return None

# ==========================================
# QUEUE-BASED VALIDATION SYSTEM
# ==========================================

@dataclass
class TransferValidationTask:
    clave_rastreo: str
    emisor: str
    receptor: str
    monto: float
    fecha: datetime
    last_tried: datetime
    retry_count: int
    order_no: str
    account_number: str

class TransferValidationQueue:
    def __init__(self):
        self.queue: List[TransferValidationTask] = []
    
    async def add_task(self, task: TransferValidationTask):
        self.queue.append(task)
    
    async def get_next_task(self) -> Optional[TransferValidationTask]:
        now = datetime.now()
        for i, task in enumerate(self.queue):
            if now - task.last_tried >= timedelta(seconds=30 * (2 ** task.retry_count)):
                return self.queue.pop(i)
        return None

class TransferValidator:
    def __init__(self, queue: TransferValidationQueue, connection_manager):
        self.queue = queue
        self.connection_manager = connection_manager
    
    async def process_queue(self):
        """Process the validation queue continuously"""
        while True:
            task = await self.queue.get_next_task()
            if task:
                await self.process_task(task)
            await asyncio.sleep(1)  # Avoid tight loop
    
    async def process_task(self, task: TransferValidationTask):
        """Process a single validation task"""
        try:
            validation_successful = await validate_transfer(
                task.fecha, task.clave_rastreo, task.emisor, task.receptor,
                task.account_number, task.monto
            )
           
            if validation_successful:
                logger.info(f"Transfer validation successful for order {task.order_no}")
                await self.connection_manager.send_text_message(
                    task.account_number,
                    "Transfer validated successfully.",
                    task.order_no
                )
            else:
                logger.warning(f"Transfer validation failed for order {task.order_no}, attempt {task.retry_count + 1}")
                if task.retry_count < 5:  # Max 6 attempts (0-5)
                    task.retry_count += 1
                    task.last_tried = datetime.now()
                    await self.queue.add_task(task)
                    await self.connection_manager.send_text_message(
                        task.account_number,
                        f"Transfer validation in progress. Retry {task.retry_count} scheduled.",
                        task.order_no
                    )
                else:
                    logger.error(f"Max retries reached for order {task.order_no}. Transfer validation ultimately failed.")
                    await self.connection_manager.send_text_message(
                        task.account_number,
                        "Transfer validation failed after multiple attempts. Please check your transfer details and try again later.",
                        task.order_no
                    )
        except Exception as e:
            logger.error(f"An error occurred during transfer validation for order {task.order_no}: {str(e)}")
            await self.connection_manager.send_text_message(
                task.account_number,
                "An error occurred during transfer validation. Please try again later.",
                task.order_no
            )

    async def handle_bank_validation(
        self,
        order_data,
        buyer_bank: str,
        seller_bank: str,
        image_URL: str,
        conn,
        account: str,
        buyer_name: str
    ) -> bool:
        """Handle bank validation process for image messages."""
        try:
            # Validate SPEI codes
            emisor_code = BANK_SPEI_CODES.get(buyer_bank.lower())
            receptor_code = BANK_SPEI_CODES.get(seller_bank.lower())
            
            if not emisor_code or not receptor_code:
                logger.error(
                    f"SPEI codes not found - Order: {order_data.orderNumber}, "
                    f"Buyer Bank: {buyer_bank}, Seller Bank: {seller_bank}"
                )
                return False

            # Extract and validate tracking key
            clave_rastreo = await extract_clave_de_rastreo(
                image_URL,
                buyer_bank.upper()
            )
            if not clave_rastreo:
                logger.error(
                    f"No Clave de Rastreo found - Order: {order_data.orderNumber}, "
                    f"Bank: {buyer_bank}"
                )
                return False
            
            # Perform validation
            fecha = date.today()
            validation_successful = await retry_request(
                lambda: Transferencia.validar(
                    fecha=fecha,
                    clave_rastreo=clave_rastreo,
                    emisor=emisor_code,
                    receptor=receptor_code,
                    cuenta=order_data.account_number,
                    monto=order_data.totalPrice
                ),
                retries=5,
                delay=2,
                backoff=2
            )

            if validation_successful:
                logger.info(
                    f"Transfer validation successful - Order: {order_data.orderNumber}, "
                    f"Buyer: {buyer_name}"
                )
                
                # Get user's language for success message
                language = await LanguageSelector.check_language_preference(conn, buyer_name)
                
                if language == 'en':
                    success_message = "Perfect! Processing your release now."
                else:
                    success_message = "Listo procedo a liberar."
                
                await self.connection_manager.send_text_message(
                    account,
                    success_message,
                    order_data.orderNumber
                )
                return True

            # Log validation failure details
            logger.error(
                f"Transfer validation failed - Order: {order_data.orderNumber}, "
                f"Buyer: {buyer_name}, "
                f"Banks: {buyer_bank}->{seller_bank}, "
                f"Amount: {order_data.totalPrice}, "
                f"Clave: {clave_rastreo}"
            )
            return False

        except Exception as e:
            logger.error(
                f"Bank validation error - Order: {order_data.orderNumber}, "
                f"Error: {str(e)}\n{traceback.format_exc()}"
            )
            return False