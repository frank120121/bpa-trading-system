from database import update_anti_fraud_stage, update_kyc_status
from binance_messages import send_text_message
from lang_utils import payment_concept, payment_warning
from binance_bank_deposit import get_payment_details

async def handle_anti_fraud(buyer_name, seller_name, conn, anti_fraud_stage, response, order_no, ws):
    def get_next_question(stage, seller_name):
        if stage == 0:
            return (
                    f"Hola {seller_name}. Por su seguridad, antes de poder proceder con el intercambio, es necesario verificar que no esté siendo víctima de un fraude.\n\n"
                    f"Responda con un 'Si' o un 'No' a las siguientes preguntas.\n\n"
                    f"¿Le han ofrecido un trabajo, una oportunidad de inversión o una gran oferta que requiere invertir a través de Bitcoin, USDT, o alguna criptomoneda?"
                )
        elif stage == 1:
            return "¿Alguien lo/la está presionando para realizar el pago?"
        elif stage == 2:
            return "¿Está consciente de que las transacciones con este tipo de activos son irreversibles y que, una vez enviados, no hay manera de recuperarlos?"

    if response.lower() not in ['sí', 'si', 'no', 'start_pro']:
        await send_text_message(ws, "Respuesta no reconocida. Por favor, responda con 'Si' o 'No'.", order_no)

        # Re-send the previous question as a reminder
        if anti_fraud_stage >= 0:
            prev_question = get_next_question(anti_fraud_stage, seller_name)
            await send_text_message(ws, prev_question, order_no)

        return

    if (anti_fraud_stage in [0, 1] and response.lower() == 'sí') or (anti_fraud_stage in [2] and response.lower() == 'no'):
        await send_text_message(ws, "Por razones de seguridad, no podemos continuar con este intercambio. Es posible que este siendo víctima de un fraude. Por favor cancele la orden y no realice ninguna transferencia ya que puede perder su dinero.", order_no)
        return

    # Update the stage based on the response
    if anti_fraud_stage == 0 and response.lower() == 'no':
        anti_fraud_stage += 1
    elif anti_fraud_stage == 1 and response.lower() == 'no':
        anti_fraud_stage += 1
    elif anti_fraud_stage == 2 and response.lower() in ['sí', 'si']:
        anti_fraud_stage += 1
        await update_kyc_status(conn, buyer_name, 1)

    # Update the stage in the database
    await update_anti_fraud_stage(conn, buyer_name, anti_fraud_stage)

    # Now return the appropriate response based on the updated stage
    if anti_fraud_stage <= 2:
        next_question = get_next_question(anti_fraud_stage, seller_name)
        await send_text_message(ws, next_question, order_no)
    elif anti_fraud_stage >= 3:
        payment_details = await get_payment_details(conn, order_no)
        await send_text_message(ws, payment_warning, order_no)
        await send_text_message(ws, payment_details, order_no)
        await send_text_message(ws, payment_concept, order_no)
