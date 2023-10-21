from database import update_anti_fraud_stage



class AntiFraud:
    def __init__(self, buyer_name, seller_name, bank_name, account_number, conn, anti_fraud_stage=1):
        self.stage = anti_fraud_stage
        self.buyer_name = buyer_name
        self.seller_name = seller_name
        self.bank_name = bank_name
        self.account_number = account_number


    def get_next_question(self):
        if self.stage == 1:
            return ("Hola, soy Nebula. Por su seguridad, antes de poder proceder con el intercambio, es necesario verificar que no esté siendo víctima de un fraude. "
                    "Responda con un \"Si\" o un \"No\" a las siguientes preguntas.\n\n"
                    "¿Le han ofrecido un trabajo, una oportunidad de inversión o una gran oferta que requiere invertir a través de Bitcoin, USDT, o alguna criptomoneda?")
        elif self.stage == 2:
            return "¿Alguien lo está presionando para realizar el pago?"
        elif self.stage == 3:
            return f"¿Está de acuerdo con que este es solo un intercambio entre {self.buyer_name} y {self.seller_name}, y que {self.buyer_name} no se hará responsable de ningún tipo de pérdida que usted incurra después de completar este intercambio?"
        elif self.stage == 4:
            return "¿Está consciente de que las transacciones con este tipo de activos son irreversibles y que, una vez enviados, no hay manera de recuperarlos?"

    def handle_response(self, response):
        if response.lower() not in ['sí', 'si', 'no']:
            return "Respuesta no reconocida. Por favor, responda con 'Si' o 'No'."

        if self.stage == 1 and response.lower() == 'no':
            self.stage += 1
            return self.get_next_question()
        elif self.stage == 2 and response.lower() == 'no':
            self.stage += 1
            return self.get_next_question()
        elif self.stage == 3 and response.lower() == 'sí':
            self.stage += 1
            return self.get_next_question()
        elif self.stage == 4 and response.lower() == 'sí':
            return (f"Al enviar el pago, está confirmando que está de acuerdo con los términos y que toda responsabilidad del uso y pérdidas después de este intercambio son únicamente suyas. "
                    f"Es su responsabilidad realizar la investigación necesaria antes de cualquier inversión.\n\n"
                    f"Los detalles para el pago son:\n\n"
                    f"Nombre de banco: {self.bank_name}\n"
                    f"Nombre del beneficiario: {self.seller_name}\n"
                    f"Número de CLABE: {self.account_number}\n"
                    f"Para que no se cancele el intercambio de forma automática, puede marcar el intercambio como pagado en la opción que dice 'Realizar Pago'. Para ayuda, escriba la palabra 'ayuda'.")
        else:
            # If any response is 'yes' in stages 1 and 2 or 'no' in stages 3 and 4, it might indicate potential fraud, so you may return a warning message or abort the transaction.
            return "Por razones de seguridad, no podemos continuar con este intercambio. Por favor, contacte al soporte si tiene más preguntas."
