from common_vars import ProhibitedPaymentTypes

def get_message_by_language(language, status, buyer_name=None):
    STATUS_MESSAGES = {
        2: {
            'es': "Estamos validando su pago, por favor permitame unos minutos para verificar. Gracias por su paciencia",
            'en': "Your payment is under review, please allow the team a few more minutes. Thank you for your patience."
        },
        1: {
            'es': [
                "Por favor enviar el pago a los detalles del anuncio. Pagos provenientes de {ProhibitedPaymentTypes} estan PROHIBIDOS y seran APELADOS.",
                "Para el concepto estas son opciones validas: pago, o su nombre ({buyer_name})."
            ],
            'en': [
                "Hello {buyer_name}, thank you for your order! Please remember that we only accept payments from accounts that are in your name.",
                "Thank you for your understanding."
            ]
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
            'es': "Le agredeceria unos minutos para poder verificar el problemas, sigo con usted.",
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

    messages = STATUS_MESSAGES.get(status, {}).get(language, None)

    if messages:
        if isinstance(messages, list):
            formatted_messages = [msg.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes) for msg in messages]
            return formatted_messages
        else:
            return [messages.format(buyer_name=buyer_name, ProhibitedPaymentTypes=ProhibitedPaymentTypes)]

    return None