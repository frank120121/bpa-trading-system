# bpa/lang_utils.py
from typing import Callable, Dict, Union
from utils.common_vars import ProhibitedPaymentTypes
from utils.logging_config import setup_logging

logger = setup_logging(log_filename='binance_main.log')

# DEPRECATED: Keep for emergency fallback only
def determine_language(fiat_unit):
    """DEPRECATED: Use LanguageSelector.check_language_preference() instead."""
    lang_mappings = {'MXN': 'es', 'USD': 'en'}
    return lang_mappings.get(fiat_unit, 'es')  # Default to Spanish

# Updated to accept language parameter directly
async def get_menu_for_order(language, order_status):
    """Get menu for order using user's language preference."""
    return get_menu_by_language(language, order_status)

# Updated to accept language parameter directly
async def get_default_help(language):
    """Get default help using user's language preference."""
    return (
        "Si tiene alguna duda o necesita ayuda, solo escriba 'ayuda' en el chat y le presentaré un menú de opciones."
        if language == 'es' else
        "If you have any questions or need assistance, just type 'help' in the chat, and I'll present you with an options menu."
    )

# This function already accepts language parameter - no changes needed
async def get_response_for_menu_choice(language, status, choice, buyer_name=None):
    response = MENU_RESPONSES.get(status, {}).get(language, {}).get(choice)
    if response:
        if isinstance(response, list):
            response = "\n\n".join(
                msg.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes) for msg in response
            )
        else:
            response = response.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes)
    return response

# This function already accepts language parameter - no changes needed
async def is_valid_choice(language, status, choice):
    valid_choices = MENUS.get(status, {}).get(language, [])
    return choice in range(1, len(valid_choices) + 1)

# Updated to accept language parameter directly
async def get_invalid_choice_reply(language):
    """Get invalid choice reply using user's language preference."""
    return "Opción no válida." if language == 'es' else "Invalid choice."

# This function already accepts language parameter - no changes needed
async def get_message_by_language(language, status, buyer_name=None):
    messages = STATUS_MESSAGES.get(status, {}).get(language, None)
    if messages:
        if isinstance(messages, list):
            messages = [msg.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes) for msg in messages]
        else:
            messages = [messages.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes)]
    return messages

# Updated to accept language parameter
async def verified_customer_greeting(buyer_name, language='es'): 
    """Get verified customer greeting in user's preferred language."""
    if language == 'en':
        return (
            f"Hello {buyer_name}!\n\n"
            f"It's a pleasure to assist you. I'm online and ready to help. "
            f"I'll send you the payment details in a moment."
        )
    else:  # Spanish (default)
        return (
            f"¡Hola {buyer_name}!\n\n"
            f"Es un placer atenderte. Estoy en linea y al pendiente. En un momento te envio los detalles del pago."
        )

# Updated to support language parameter for payment warning
async def payment_warning_localized(language='es'):
    """Get payment warning in user's preferred language."""
    if language == 'en':
        return (
            f"Payments from {ProhibitedPaymentTypes} are PROHIBITED and will be APPEALED.\n\n"
            f"By sending the payment, you are confirming that you agree to the terms and that all responsibility "
            f"for the use and losses of assets after this exchange are solely yours.\n\n"
            f"It is your responsibility to conduct the necessary research before any investment as losses are real and irreversible.\n\n"
        )
    else:  # Spanish
        return (
            f"Pagos provenientes de {ProhibitedPaymentTypes} estan PROHIBIDOS y seran APELADOS.\n\n"
            f"Al enviar el pago, está confirmando que está de acuerdo con los términos y que toda responsabilidad del uso y pérdidas de los activos "
            f"después de este intercambio son únicamente suyas.\n\n"
            f"Es su responsabilidad realizar la investigación necesaria antes de cualquier inversión ya que las perdidas son reales e irreversibles.\n\n"
        )

# Global variables for status messages, menus, and menu responses
STATUS_MESSAGES, MENUS, MENU_RESPONSES = {}, {}, {}

# Function to get menu by language - no changes needed
def get_menu_by_language(language, status):
    return MENUS.get(status, {}).get(language, [])

STATUS_MESSAGES = {
    1: {
        'es': [
            "**********IMPORTANTE!!!**********\n\n",
            "Hola {buyer_name}. Para recibir los datos de deposito es necesario confirmar que cumpla con los terminos del anuncio.",

        ],
        'en': [
            "Hello {buyer_name}. Please reply with just 'YES' or 'NO' to the following:",
        ],
    },
    2: {
        'es': "Si aun no envia el comprobante de pago por favor enviarlo ahora para poder liberar la orden(requerido). De lo contrario por favor ignorar este mensaje.",
        'en': "If you have not sent the proof of payment, please send it now so I can release the order(required). If you have already sent it, please ignore this message. For help type \"HELP\"."
    },
    3: {
        'es': "Para poder realizar el pago lo mas rapido posible, me podrias ayudar con el numero de clabe interbancaria en caso de que no la tenga agregada.",
        'en': "To make the payment as quickly as possible, could you please provide me with the paymenet details in case I don't have them saved."
    },
    4: {
        'es': (
            "Activo depositado en su billetara de fondos. Por favor no olvide calificar esta transaccion.\n\n"
            "Muchas gracias por su apoyo pase un excelente dia 😊"
        ),
        'en': "This order is now completed, you can check in your funds or spot wallet please."
    },
    5: {
        'es': "Le agredeceria unos minutos para poder verificar el problema, sigo con usted.",
        'en': "Please allow me a few minutes to check the order."
    },
    6: {
        'es': "Esta orden ya esta cancelada, si require asistencia por favor abrir una nueva ordern o contactar a soporte.",
        'en': "This order is cancelled if you still require assistance please open a new order or contact support."
    },
    7: {
        'es': (
            "veo que la orden se cancelo. Si envio el pago y la orden se cancelo no se preocupe, puede abrir una nueva orden sin tener que pagar dos veces. "
            "Solo adjunte el comprobante de pago y seleccione la opción que dice 'realizar pago' o 'transferir notificar al vendedor' con gusto lo atendere. (respuesta automatica)"
        ),
        'en': "Order has been automatically cancelled. If you have sent the payment, please open a new order and attach your proof of your payment."
    },
    8: {
        'es': 'Listo el pago ya se envio por favor verificar el deposito en su cuenta y proceder a liberar la orden. Muchas gracias por su apoyo pase un excelente dia.',
        'en': 'The payment has been sent, please verify you have received the deposit and release the order. Thank you have a great day!'
    },
    9: {
        'es': (
            "Debido a que violó los términos del anuncio se procede con una apelacion de la orden.\n\n"
            "En caso de cualquier retorno, se require un lapso de hasta 24 horas para poder realizar el retorno.\n" 
            "En caso de retorno proporcione el número de CLABE INTERBANCARIA y nombre de BENEFICIARIO para poder proceder lo más rápido posible.\n\n"
            "Por favor no se desespere, realizaré el retorno en cuanto me sea posible. Tome en cuenta que tengo otras órdenes pendientes.\n\n"
            "Muchas gracias por su comprensión.(respuesta automatica)"
        ),
        'en': "Order is under appeal due to violation of terms. Please wait while the team resolves your order."
    },
    100: {
        'es': "Enseguida verifico.",
        'en': "One moment please, I will check."
    }
}

MENUS = {
    1: {
        'es': [
            "Le presento las opciones disponibles del 1-3:",
            "1. Opciones de pago.",
            "2. Que incluir en el concepto/referencia.",
            "3. Terminos de la orden.",
            "Por favor solo introducir el numero correspondiente."
        ],
        'en': [
            "Available options 1-3:",
            "1. Payment options.",
            "2. What to include in the concept/reference.",
            "3. Order terms.",
            "Please enter the corresponding number only."
        ]
    },
    2: {
        'es': [
            "Le presento las opciones disponibles del 1-5:",
            "",
            "1. Estado del pago.",
            "2. Cómo enviar prueba de pago.",
            "3. ¿Qué hacer si enviaste una cantidad incorrecta?",
            "4. ¿Necesitas más tiempo para realizar el pago?",
            "5. Tiempo de espera para transacciones BBVA.",
            "",
            "Por favor solo introducir el numero correspondiente."
        ],
        'en': [
            "Available options 1-4:",
            "",
            "1. Payment status.",
            "2. How to send payment proof.",
            "3. What to do if you sent the wrong amount?",
            "4. Need more time to make the payment?",
            "",
            "Please enter the corresponding number only."
        ]
    }
}

MENU_RESPONSES = {
    1: {
        'es': {
            1: (
                "Para ver las opciones de pago por favor seleccione la opcion Realizar Pago en la parte superior > Seleccione el metodo de pago "
                "> Selecione la opcion que dice Transferido, notificar al vendedor despues de realizar el pago."
            ),
            2: " Para el concepto estas son opciones validas: pago, o su nombre ({buyer_name}).",
            3: "Pagos provenientes de {ProhibitedPaymentTypes} estan PROHIBIDOS y seran APELADOS."
        },
        'en': {
            1: (
                "To see payment options, please select 'Make Payment' at the top > Select payment method "
                "> Select the option that says 'Transferred, notify seller after payment'."
            ),
            2: "For the concept/reference, these are valid options: payment, or your name ({buyer_name}).",
            3: "Payments from {ProhibitedPaymentTypes} are PROHIBITED and will be APPEALED."
        }
    },
    2: { 
        'es': {
            1: "Estamos validando su pago, por favor permitame unos minutos para verificar. Gracias por su paciencia",
            2: "Puedes enviar la prueba de pago selecionando el boton (+) > ALBUM > y la captura que desea adjuntar.",
            3: "Si enviaste una cantidad incorrecta, deberas cancelar esta orden primero y despues abrir una nueva orden por la cantidad correcta.",
            4: (
                "Si necesitas más tiempo para realizar el pago, debido a que necesitas dar de alta la cuenta podemos esperar. "
                "Siempre y cuando no se demore mas de 1 hora, de lo contrario la orden sera APELADA."
            ),
            5: [
                "El tiempo de espera para transacciones BBVA puede llegar a ser hasta de 4 horas.",
                (
                    "Puede verificar el estado de la transferncia en su app BBVA ingresando a la app > selecione la cuenta desde donde realizo el pago "
                    "> En la parte de abajo seleccione la opcion: Ver todos > el pago que realizo > y entre la cantidad y la fecha la va aparecer "
                    "Establecido cuando el pago se haga realizado o en transito si aun no se envia."
                ),
                "Para pagos desde la web le va aparecer como liquidado cuando el pago sea enviado, de lo contrario aparece como pendiente.",
            ],
        },
        'en': {
            1: "We are validating your payment, please allow me a few minutes to verify. Thank you for your patience.",
            2: "You can send proof of payment by selecting the (+) button > ALBUM > and the screenshot you want to attach.",
            3: "If you sent the wrong amount, you must cancel this order first and then open a new order for the correct amount.",
            4: "If you need more time to make the payment, please cancel the order and open a new one once you are ready.",
        }
    }
}

# Bilingual messages (keep as-is since they serve both languages)
transaction_denied = (
    "For security reasons, I cannot sell to you. Please cancel the order.\n\n"
    "Por razones de seguridad no es posible proceder. Por favor cancele la orden."
)

invalid_country = (
    "Lo sentimos, actualmente no estamos aceptando pagos de este país. Estamos trabajando constantemente para expandir la lista de países aceptados.\n\n"
    "Gracias por elegirnos, que tenga un excelente día.\n\n"
    "sorry, we are not currently accepting payments from this country. We are constantly working to expand the list of accepted countries.\n\n"
    "Thank you for choosing us, have a great day.\n\n"
    "\n\n"
    "En caso de que este utilizando un VPN, por favor desactívelo he intentarlo mas tarde.\n\n"
    "If you are using a VPN, please disable it and try again later."
)

# Updated anti-fraud messages to support both languages
def get_anti_fraud_messages(language='es'):
    """Get anti-fraud messages in the specified language."""
    if language == 'en':
        return {
            "employment_check": (
                "Are you buying because someone has offered you employment, investment with high returns, "
                "or promises of profits in exchange for you sending them these cryptocurrencies? (1/3)"
            ),
            "pressure_check": (
                "Do you feel unusual pressure or urgency from someone to complete this payment immediately? (2/3)"
            ),
            "refund_agreement": lambda order_no: (
                f"Do you understand that once the order ({order_no}) is successfully completed, "
                "there is no possibility of refund or return from the seller? (3/3)"
            ),
            "bank_request": (
                "Thank you for completing the questions. Now, to provide you with more efficient service, "
                "could you tell us the name of the bank you will use to make the payment?"
            ),
            "account_ownership": lambda buyer_name: (
                f"Perfect, we accept your bank. Finally, the bank account you will use "
                f"to make the payment, is it in your name? ({buyer_name})"
            ),
            "oxxo_cash_payment": "For the OXXO payment method, are you making the payment in cash?",
            "bank_verification_failed": lambda banks_list: (
                f"We could not verify the bank provided. Please make sure to choose "
                f"one of the following accepted banks: {banks_list}"
            )
        }
    else:  # Spanish
        return {
            "employment_check": (
                "¿Esta usted comprando porque le han ofrecido empleo, inversión con altos retornos "
                "o promesas de ganancias a cambio de que usted les envie estas criptomonedas? (1/3)"
            ),
            "pressure_check": (
                "¿Siente presión o urgencia inusual por parte de alguien para completar este pago de inmediato? (2/3)"
            ),
            "refund_agreement": lambda order_no: (
                f"¿Está usted de acuerdo que una vez completada la orden({order_no}) exitosamente, "
                "no hay posibilidad de reembolso o devolucion por parte del vendedor? (3/3)"
            ),
            "bank_request": (
                "Muchas gracias por completar las preguntas, ahora para brindarle un servicio más eficiente, "
                "¿podría indicarnos el nombre del banco que utilizará para realizar el pago?"
            ),
            "account_ownership": lambda buyer_name: (
                f"Perfecto si aceptamos su banco. Por ultimo, la cuenta bancaria que utilizará "
                f"para realizar el pago, ¿está a su nombre? ({buyer_name})"
            ),
            "oxxo_cash_payment": "Para el método de pago OXXO, ¿está realizando el pago en efectivo?",
            "bank_verification_failed": lambda banks_list: (
                f"No pudimos verificar el banco proporcionado. Por favor, asegúrese de elegir "
                f"uno de los siguientes bancos aceptados: {banks_list}"
            )
        }

# Keep original ANTI_FRAUD_MESSAGES for backward compatibility (Spanish only)
MessageTemplate = Callable[[str], str]
MessagesDict = Dict[str, Union[str, MessageTemplate]]

ANTI_FRAUD_MESSAGES: MessagesDict = get_anti_fraud_messages('es')

# Updated customer verification messages to support both languages
def get_customer_verification_messages(language='es'):
    """Get customer verification messages in the specified language."""
    if language == 'en':
        return {
            "bank_confirmation": lambda buyer_bank: f"Are you sending the payment from {buyer_bank}? (yes/no)",
            "bank_request": "No problem. Could you tell us the name of the bank you will use to make the payment?",
            "account_ownership": lambda buyer_name: f"Perfect, we accept your bank. Finally, the bank account you will use to make the payment, is it in your name? ({buyer_name})",
            "bank_verification_failed": lambda accepted_banks_list: f"We could not verify the bank provided. Please make sure to choose one of the following accepted banks: {accepted_banks_list}"
        }
    else:  # Spanish
        return {
            "bank_confirmation": lambda buyer_bank: f"Esta usted enviado el pago desde {buyer_bank}? (si/no)",
            "bank_request": "No hay problema. ¿Podría indicarnos el nombre del banco que utilizará para realizar el pago?",
            "account_ownership": lambda buyer_name: f"Perfecto si aceptamos su banco. Por ultimo, la cuenta bancaria que utilizará para realizar el pago, ¿está a su nombre? ({buyer_name})",
            "bank_verification_failed": lambda accepted_banks_list: f"No pudimos verificar el banco proporcionado. Por favor, asegúrese de elegir uno de los siguientes bancos aceptados: {accepted_banks_list}"
        }

# Keep original for backward compatibility (Spanish only)
BankMessageTemplate = Callable[[str], str]
MessageTemplate = Dict[str, Union[str, BankMessageTemplate]]

CUSTOMER_VERIFICATION_MESSAGES = get_customer_verification_messages('es')

# Individual anti-fraud response messages for different languages
anti_fraud_not_valid_response_es = "Por favor responda exactamente con un 'Si' o un 'No' a la siguiente pregunta:"
anti_fraud_not_valid_response_en = "Please respond exactly with 'Yes' or 'No' to the following question:"

anti_fraud_user_denied_es = "Por razones de seguridad, no podemos continuar con este intercambio. Gracias por su comprensión."
anti_fraud_user_denied_en = "For security reasons, we cannot continue with this exchange. Thank you for your understanding."

anti_fraud_possible_fraud_es = (
    "Por razones de seguridad, no podemos continuar con este intercambio. Es posible que esté siendo víctima de un fraude. "
    "Por favor cancele la orden y no realice ninguna transferencia ya que puede perder su dinero."
)
anti_fraud_possible_fraud_en = (
    "For security reasons, we cannot continue with this exchange. You may be a victim of fraud. "
    "Please cancel the order and do not make any transfers as you may lose your money."
)

anti_fraud_stage3_es = (
    "Lo sentimos, actualmente no estamos aceptando pagos de este banco. Estamos trabajando constantemente para expandir la lista de bancos aceptados.\n\n"
    "Gracias por elegirnos, que tenga un excelente día."
)
anti_fraud_stage3_en = (
    "Sorry, we are not currently accepting payments from this bank. We are constantly working to expand the list of accepted banks.\n\n"
    "Thank you for choosing us, have a great day."
)

# Helper functions to get localized anti-fraud messages
def get_anti_fraud_not_valid_response(language='es'):
    return anti_fraud_not_valid_response_en if language == 'en' else anti_fraud_not_valid_response_es

def get_anti_fraud_user_denied(language='es'):
    return anti_fraud_user_denied_en if language == 'en' else anti_fraud_user_denied_es

def get_anti_fraud_possible_fraud(language='es'):
    return anti_fraud_possible_fraud_en if language == 'en' else anti_fraud_possible_fraud_es

def get_anti_fraud_stage3(language='es'):
    return anti_fraud_stage3_en if language == 'en' else anti_fraud_stage3_es

# Keep the original variables for backward compatibility (Spanish)
anti_fraud_stage3 = anti_fraud_stage3_es
anti_fraud_not_valid_response = anti_fraud_not_valid_response_es
anti_fraud_user_denied = anti_fraud_user_denied_es
anti_fraud_possible_fraud = anti_fraud_possible_fraud_es

# Keep the original payment_warning for backward compatibility
payment_warning_mxn = (
    f"Pagos provenientes de {ProhibitedPaymentTypes} estan PROHIBIDOS y seran APELADOS.\n\n"
    f"Al enviar el pago, está confirmando que está de acuerdo con los términos y que toda responsabilidad del uso y pérdidas de los activos "
    f"después de este intercambio son únicamente suyas.\n\n"
    f"Es su responsabilidad realizar la investigación necesaria antes de cualquier inversión ya que las perdidas son reales e irreversibles.\n\n"
)

payment_warning_usd = (
    "THIRD PARTY payments are PROHIBITED and will be APPEALED.\n\n"
    "By sending the payment, you are confirming that you agree to the terms and that all responsibility "
    "for the use and losses of assets after this exchange are solely yours.\n\n"
    "It is your responsibility to conduct the necessary research before any investment as losses are real and irreversible.\n\n"
)