#bpa/TEST_binance_cep_2.py
import asyncio
from datetime import datetime
from cep import Transferencia
import pytesseract
import re
import logging
from abc import ABC, abstractmethod
from utils.common_utils import download_image
# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


    
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

async def validate_transfer(fecha, clave_rastreo, emisor, receptor, cuenta, monto):
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