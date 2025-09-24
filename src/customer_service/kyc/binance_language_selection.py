# binance_language_selection.py
from typing import Optional, Tuple

from data.database.operations.binance_db_get import get_user_language_preference, get_language_selection_stage
from data.database.operations.binance_db_set import set_user_language_preference, set_language_selection_stage
from utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

class LanguageSelector:
    """Handles language selection process for users."""
    
    # Language configuration
    SUPPORTED_LANGUAGES = {
        'en': {
            'name': 'English',
            'code': 'en',
            'triggers': ['1', 'english', 'en', 'eng'],
            'confirmation': "✅ Language set to English. Let's continue!"
        },
        'es': {
            'name': 'Español', 
            'code': 'es',
            'triggers': ['2', 'español', 'espanol', 'spanish', 'es', 'spa'],
            'confirmation': "✅ Idioma configurado en Español. ¡Continuemos!"
        }
    }
    
    LANGUAGE_PROMPT = (
        "🌐 Please select your preferred language / Por favor selecciona tu idioma preferido:\n\n"
        "For English, type: 1 or English\n"
        "Para Español, escribe: 2 o Español\n\n"
        "📱 Simply reply with your choice"
    )
    
    INVALID_SELECTION_MESSAGE = (
        "❌ Invalid selection. Please choose:\n"
        "1 or English for English\n"
        "2 or Español for Spanish\n\n"
        "❌ Selección inválida. Por favor elige:\n"
        "1 o English para Inglés\n" 
        "2 o Español para Español"
    )

    @classmethod
    async def check_language_preference(cls, conn, buyer_name: str) -> Optional[str]:
        """Check if user has a language preference set."""
        try:
            return await get_user_language_preference(conn, buyer_name)
        except Exception as e:
            logger.error(f"Error checking language preference for {buyer_name}: {str(e)}")
            return None

    @classmethod
    async def is_language_selection_pending(cls, conn, buyer_name: str) -> bool:
        """Check if user is currently in language selection process."""
        try:
            stage = await get_language_selection_stage(conn, buyer_name) or 0
            return stage == 1
        except Exception as e:
            logger.error(f"Error checking language selection stage for {buyer_name}: {str(e)}")
            return False

    @classmethod
    async def initiate_language_selection(
        cls, 
        conn, 
        buyer_name: str, 
        connection_manager, 
        account: str, 
        order_no: str
    ) -> bool:
        """
        Initiate language selection process for a user.
        Returns True if successfully initiated, False otherwise.
        """
        try:
            # Send language selection prompt
            await connection_manager.send_text_message(
                account, 
                cls.LANGUAGE_PROMPT, 
                order_no
            )
            
            # Set language selection stage to indicate we're waiting for response
            await set_language_selection_stage(conn, buyer_name, 1)
            
            logger.info(f"Language selection initiated for {buyer_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error initiating language selection for {buyer_name}: {str(e)}")
            return False

    @classmethod
    async def process_language_selection(
        cls,
        conn,
        buyer_name: str,
        user_input: str,
        connection_manager,
        account: str,
        order_no: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Process user's language selection response.
        
        Returns:
            Tuple[bool, Optional[str]]: (success, selected_language_code)
            - success: True if valid selection made, False if invalid
            - selected_language_code: Language code if successful, None if invalid
        """
        try:
            normalized_input = user_input.lower().strip()
            selected_language = None
            
            # Find matching language
            for lang_code, lang_config in cls.SUPPORTED_LANGUAGES.items():
                if normalized_input in lang_config['triggers']:
                    selected_language = lang_code
                    break
            
            if selected_language:
                # Valid selection - save preference
                success = await set_user_language_preference(conn, buyer_name, selected_language)
                
                if success:
                    # Clear language selection stage
                    await set_language_selection_stage(conn, buyer_name, 0)
                    
                    # Send confirmation in selected language
                    confirmation_msg = cls.SUPPORTED_LANGUAGES[selected_language]['confirmation']
                    await connection_manager.send_text_message(
                        account, 
                        confirmation_msg, 
                        order_no
                    )
                    
                    logger.info(f"Language '{selected_language}' set for user {buyer_name}")
                    return True, selected_language
                else:
                    logger.error(f"Failed to save language preference for {buyer_name}")
                    return False, None
            else:
                # Invalid selection - send error message
                await connection_manager.send_text_message(
                    account, 
                    cls.INVALID_SELECTION_MESSAGE, 
                    order_no
                )
                logger.warning(f"Invalid language selection '{user_input}' from {buyer_name}")
                return False, None
                
        except Exception as e:
            logger.error(f"Error processing language selection for {buyer_name}: {str(e)}")
            return False, None

    @classmethod
    async def ensure_language_set(
        cls,
        conn,
        buyer_name: str,
        connection_manager,
        account: str,
        order_no: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Ensure user has a language preference set.
        
        Returns:
            Tuple[bool, Optional[str]]: (language_is_set, language_code)
            - language_is_set: True if language is already set, False if selection was initiated
            - language_code: The language code if set, None if selection initiated
        """
        try:
            # Check if user already has language preference
            current_language = await cls.check_language_preference(conn, buyer_name)
            
            if current_language:
                logger.debug(f"User {buyer_name} already has language: {current_language}")
                return True, current_language
            
            # Check if already in selection process
            if await cls.is_language_selection_pending(conn, buyer_name):
                logger.debug(f"User {buyer_name} already in language selection process")
                return False, None
            
            # Initiate language selection
            success = await cls.initiate_language_selection(
                conn, buyer_name, connection_manager, account, order_no
            )
            
            if success:
                logger.info(f"Language selection process initiated for {buyer_name}")
            else:
                logger.error(f"Failed to initiate language selection for {buyer_name}")
            
            return False, None
            
        except Exception as e:
            logger.error(f"Error ensuring language set for {buyer_name}: {str(e)}")
            # Return True to avoid blocking the process, but log the fallback
            logger.warning(f"Using fallback language 'es' for {buyer_name} due to error")
            return True, 'es'  # Default fallback

    @classmethod
    def get_language_name(cls, language_code: str) -> str:
        """Get human-readable language name from code."""
        return cls.SUPPORTED_LANGUAGES.get(language_code, {}).get('name', 'Unknown')

    @classmethod
    def is_supported_language(cls, language_code: str) -> bool:
        """Check if language code is supported."""
        return language_code in cls.SUPPORTED_LANGUAGES

    @classmethod
    def get_supported_languages(cls) -> dict:
        """Get all supported languages configuration."""
        return cls.SUPPORTED_LANGUAGES.copy()

    @classmethod
    def validate_language_code(cls, language_code: str) -> bool:
        """Validate that a language code is properly formatted and supported."""
        if not language_code or not isinstance(language_code, str):
            return False
        return language_code.lower() in cls.SUPPORTED_LANGUAGES

    @classmethod
    async def get_user_language_display_name(cls, conn, buyer_name: str) -> str:
        """Get the display name of user's selected language."""
        try:
            language_code = await cls.check_language_preference(conn, buyer_name)
            if language_code:
                return cls.get_language_name(language_code)
            return "Not Set"
        except Exception as e:
            logger.error(f"Error getting language display name for {buyer_name}: {str(e)}")
            return "Unknown"

    @classmethod
    async def reset_language_preference(
        cls,
        conn,
        buyer_name: str,
        connection_manager=None,
        account: str = None,
        order_no: str = None
    ) -> bool:
        """Reset user's language preference and initiate new selection."""
        try:
            # Clear existing preferences
            await set_user_language_preference(conn, buyer_name, None)
            await set_language_selection_stage(conn, buyer_name, 0)
            
            # If connection details provided, initiate new selection
            if connection_manager and account and order_no:
                return await cls.initiate_language_selection(
                    conn, buyer_name, connection_manager, account, order_no
                )
            
            logger.info(f"Language preference reset for {buyer_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error resetting language preference for {buyer_name}: {str(e)}")
            return False

    @classmethod
    async def change_language_preference(
        cls,
        conn,
        buyer_name: str,
        new_language: str,
        connection_manager,
        account: str,
        order_no: str
    ) -> bool:
        """Allow existing users to change their language preference."""
        try:
            if not cls.validate_language_code(new_language):
                logger.error(f"Invalid language code: {new_language}")
                return False
            
            # Update language preference
            success = await set_user_language_preference(conn, buyer_name, new_language.lower())
            
            if success:
                # Send confirmation in new language
                confirmation_msg = cls.SUPPORTED_LANGUAGES[new_language.lower()]['confirmation']
                await connection_manager.send_text_message(
                    account, 
                    confirmation_msg, 
                    order_no
                )
                
                logger.info(f"Language changed to '{new_language}' for user {buyer_name}")
                return True
            else:
                logger.error(f"Failed to update language preference for {buyer_name}")
                return False
                
        except Exception as e:
            logger.error(f"Error changing language preference for {buyer_name}: {str(e)}")
            return False