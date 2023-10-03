from common_vars import ProhibitedPaymentTypes

def determine_language(order_details):
    fiat_unit = order_details.get('fiat_unit')
    lang_mappings = {'MXN': 'es', 'USD': 'en'}
    return lang_mappings.get(fiat_unit, 'en')
def get_menu_for_order(order_details):
    language = determine_language(order_details)
    menu = get_menu_by_language(language, order_details.get('order_status'))
    return menu
def get_default_reply(order_details):
    language = determine_language(order_details)
    if language == 'es':
        return "Si tiene alguna duda o necesita ayuda, solo escriba 'ayuda' en el chat y le presentaré un menú de opciones."
    else:
        return "If you have any questions or need assistance, just type 'help' in the chat, and I'll present you with an options menu."
def get_response_for_menu_choice(language, status, choice, buyer_name=None):
    response = MENU_RESPONSES.get(status, {}).get(language, {}).get(choice)
    
    if response is not None:
        if isinstance(response, list):
            formatted_response = [msg.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes) for msg in response]
            return "\n\n".join(formatted_response)
        else:
            return response.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes)

    return None


def is_valid_choice(language, status, choice):
    valid_choices = MENUS.get(status, {}).get(language, [])
    return choice in range(1, len(valid_choices) + 1)

def get_invalid_choice_reply(order_details):
    language = determine_language(order_details)
    if language == 'es':
        return "Opción no válida. Si tiene dudas, escriba 'ayuda' en el chat."
    else:
        return "Invalid choice. If you have questions, type 'help' in the chat."


STATUS_MESSAGES = {
    2: {
        'es': "Estamos validando su pago, por favor permitame unos minutos para verificar. Gracias por su paciencia",
        'en': "Your payment is under review, please allow the team a few more minutes. Thank you for your patience."
    },
    1: {
        'es': [
            "Hola soy Nebula, una asistente virtual. Solo se aceptan pagos de cuentas bancarias que estan a su nombre ({buyer_name}).",
            "Pagos provenientes de {ProhibitedPaymentTypes} estan PROHIBIDOS y seran APELADOS.",
            "Para el concepto estas son opciones validas: pago, o su nombre ({buyer_name}). Si tiene alguna duda o necesita ayuda solo teclee ayuda en el chat y le presentare un menu de opciones.",

        ],
        'en': [
            "Hello, I'm Nebula, an automated assistant here to streamline the trading process. We only accept payments from bank accounts registered in your name, {buyer_name}.",
            "Payments from {ProhibitedPaymentTypes} are PROHIBITED and will be APPEALED.",
            "Please send the payment to the details provided in the listing. For the payment reference, you can use 'payment' or your name, {buyer_name}.",
            "If you have any questions or need assistance, just type 'help' in the chat, and I'll present you with an options menu."
        ],
    },
    7: {
        'es': "veo que la orden se cancelo. Si envio el pago y la orden se cancelo no se preocupe, puede abrir una nueva orden sin tener que pagar dos veces. Solo adjunte el comprobante de pago y seleccione la opción que dice 'realizar pago' o 'transferir notificar al vendedor' con gusto lo atendere. (respuesta automatica)",
        'en': "Order has been automatically cancelled. If you have sent the payment, please open a new order and attach your proof of your payment."
    },
    9: {
        'es': "Debido a que violó los términos del anuncio se procede con el retorno de la transferencia. Me podrías ayudar confirmando el número de CLABE INTERBANCARIA y nombre de BENEFICIARIO para poder proceder lo más rápido posible. Por favor no se desespere, realizaré el retorno en cuanto me sea posible. Tome en cuenta que tengo otras órdenes pendientes. Muchas gracias por su comprensión, estaré enviando lo más rápido posible.(respuesta automatica)",
        'en': "Order is under appeal due to violation of terms. Please wait while the team resolves your order."
    },
    5: {
        'es': "Le agredeceria unos minutos para poder verificar el problema, sigo con usted.",
        'en': "Please allow me a few minutes to check the order."

    },
    6: {
        'es': "Esta orden ya esta cancelada, si require asistencia por favor abrir una nueva ordern o contactar a soporte.",
        'en': "This order is cancelled if you still reqiure assistance please open a new order please open a new order or contact support."
    }
    ,
    4: {
        'es': "Esta orden ya se completo con exito por favor verificar en su billetera de fondos o billetera spot.",
        'en': "This order is now completed, you can check in your funds or spot wallet please."
    }
    ,
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
            "1. Payment options.",
            "2. What to include in the concept/reference.",
            "3. Order terms."
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
            "1. Payment status.",
            "2. How to send payment proof.",
            "3. What to do if you sent the wrong amount?",
            "4. Need more time to make the payment?",
        ]
    }
}


MENU_RESPONSES = {
    1: {
        'es': {
            1: "Para ver las opciones de pago por favor seleccione la opcion Realizar Pago en la parte superior > Seleccione el metodo de pago > Selecione la opcion que dice Transferido, notificar al vendedor despues de realizar el pago.",
            2: " Para el concepto estas son opciones validas: pago, o su nombre ({buyer_name}).",
            3: "Pagos provenientes de {ProhibitedPaymentTypes} estan PROHIBIDOS y seran APELADOS."
        },
        'en': {
            1: "The payment options are X, Y, and Z.",
            2: "Please include ABC in the concept/reference of your payment.",
            3: "The terms of the order are: ..."
        }
    },
    2: { 
        'es': {
            1: "Estamos validando su pago, por favor permitame unos minutos para verificar. Gracias por su paciencia",
            2: "Puedes enviar la prueba de pago selecionando el boton (+) > ALBUM > y la captura que desea adjuntar.",
            3: "Si enviaste una cantidad incorrecta, deberas cancelar esta orden primero y despues abrir una nueva orden por la cantidad correcta.",
            4: "Si necesitas más tiempo para realizar el pago, debido a que necesitas dar de alta la cuenta podemos esperar. Siempre y cuando no se demore mas de 1 hora, de lo contrario la orden sera APELADA.",
            5: [
                "El tiempo de espera para transacciones BBVA puede llegar a ser hasta de 4 horas.",
                "Puede verificar el estado de la transferncia en su app BBVA ingresando a la app > selecione la cuenta desde donde realizo el pago > En la parte de abajo seleccione la opcion: Ver todos > el pago que realizo > y entre la cantidad y la fecha la va aparecer Establecido cuando el pago se haga realizado o en transito si aun no se envia.",
                "Para pagos desde la web le va aparecer como liquidado cuando el pago sea enviado, de lo contrario aparece como pendiente.",
            ],
        },
        'en': {
            1: "Your payment is under review, please allow the team a few more minutes. Thank you for your patience.",
            2: "You can send the proof of payment via the (+) button > ALBUM > and select the correct screenshot.",
            3: "If you sent the wrong amount, please first cancel the order and then open a new order for the correct amount.",
            4: "If you need more time to make the payment, please cancel the order and open a new one once you are ready.",
        }
    }
}

def get_menu_by_language(language, status):
    return MENUS.get(status, {}).get(language, [])

async def get_message_by_language(language, status, buyer_name=None):
    messages = STATUS_MESSAGES.get(status, {}).get(language, None)

    if messages:
        if isinstance(messages, list):
            formatted_messages = [msg.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes) for msg in messages]
            return formatted_messages
        else:
            return [messages.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes)]

    return None