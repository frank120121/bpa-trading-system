from database import update_anti_fraud_stage
from common_vars import ProhibitedPaymentTypes



class AntiFraud:
    def __init__(self, buyer_name, seller_name, bank_name, account_number, conn, anti_fraud_stage=1):
        self.stage = anti_fraud_stage
        self.buyer_name = buyer_name
        self.seller_name = seller_name
        self.bank_name = bank_name
        self.account_number = account_number
        self.conn = conn


    def get_next_question(self):
        if self.stage == 1:
            return ("Hola, soy Nebula. Por su seguridad, antes de poder proceder con el intercambio, es necesario verificar que no esté siendo víctima de un fraude. "
                    "Responda con un \"Si\" o un \"No\" a las siguientes preguntas.\n\n"
                    "¿Le han ofrecido un trabajo, una oportunidad de inversión o una gran oferta que requiere invertir a través de Bitcoin, USDT, o alguna criptomoneda?")
        elif self.stage == 2:
            return "¿Alguien lo está presionando para realizar el pago?"
        elif self.stage == 3:
            return f"¿Está de acuerdo con que este es solo un intercambio entre {self.seller_name} y {self.buyer_name}, y que {self.seller_name} no se hará responsable de ningún tipo de pérdida que usted incurra después de completar este intercambio?"
        elif self.stage == 4:
            return "¿Está consciente de que las transacciones con este tipo de activos son irreversibles y que, una vez enviados, no hay manera de recuperarlos?"

    async def handle_response(self, response):
        if response.lower() not in ['sí', 'si', 'no']:
            return "Respuesta no reconocida. Por favor, responda con 'Si' o 'No'."
        # Check for responses that might indicate potential fraud
        if (self.stage in [1, 2] and response.lower() == 'sí') or (self.stage in [3, 4] and response.lower() == 'no'):
            # This response pattern might indicate potential fraud
            return "Por razones de seguridad, no podemos continuar con este intercambio. Es posible que este siendo víctima de un fraude. Por favor cancelar la orden y no realice ninguna transferencia ya que puede perder su dinero."

        # Update the stage based on the response
        if self.stage == 1 and response.lower() == 'no':
            self.stage += 1
        elif self.stage == 2 and response.lower() == 'no':
            self.stage += 1
        elif self.stage == 3 and response.lower() == 'sí':
            self.stage += 1
        elif self.stage == 4 and response.lower() == 'sí':
            self.stage += 1

        # Update the stage in the database
        await update_anti_fraud_stage(self.conn, self.buyer_name, self.stage)

        # Now return the appropriate response based on the updated stage
        if self.stage <= 4:
            return self.get_next_question()
        else:
            return (f"Al enviar el pago, está confirmando que está de acuerdo con los términos y que toda responsabilidad del uso y pérdidas de los activos y/o el dinero después de este intercambio son únicamente suyas. "
                    f"Es su responsabilidad realizar la investigación necesaria antes de cualquier inversión ya que las perdidas son reales e irreversibles.\n\n"
                    f"Pagos provenientes de {ProhibitedPaymentTypes} estan PROHIBIDOS y seran APELADOS.\n\n"
                    f"Los detalles para el pago son:\n\n"
                    f"Nombre de banco: {self.bank_name}\n"
                    f"Nombre del beneficiario: {self.seller_name}\n"
                    f"Número de CLABE: {self.account_number}\n"
                    f"Para el concepto estas son opciones validas: pago, o su nombre ({self.buyer_name}).\n\n"
                    f"Para que no se cancele el intercambio de forma automática, puede marcar el intercambio como pagado en la opción que dice 'Realizar Pago'. Para ayuda, escriba la palabra 'ayuda'.")
