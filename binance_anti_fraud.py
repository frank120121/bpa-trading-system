from database import update_anti_fraud_stage, update_kyc_status
from binance_messages import send_text_message
from binance_blacklist import add_to_blacklist
from lang_utils import transaction_denied, payment_concept, payment_warning
from binance_bank_deposit import get_payment_details
from common_vars import NOT_ACCEPTED_BANKS

async def handle_anti_fraud(buyer_name, seller_name, conn, anti_fraud_stage, response, order_no, ws):
    questions = [
        f"¿Le han ofrecido un trabajo, una oportunidad de inversión o una gran oferta que requiere invertir a través de Bitcoin, USDT, o alguna criptomoneda? ({anti_fraud_stage + 1}/5)",
        "¿Alguien lo/la está presionando para realizar el pago? (2/5)",
        f"¿Está de acuerdo que este es solo una orden de compra entre {buyer_name} y {seller_name}, y que además {seller_name} no será responsable de ninguna devolución una vez completado la orden con éxito? (3/5)",
        "Para brindarle un servicio más eficiente, ¿podría indicarnos el nombre del banco que utilizará para realizar el pago? (4/5)",
        f"La cuenta bancaria que utilizará para realizar el pago, ¿está a su nombre? ({buyer_name}) (5/5)",
    ]

    normalized_response = response.strip().lower()
    if anti_fraud_stage >= len(questions):
        return  # No more questions

    if anti_fraud_stage == 3 and any(bank.lower() in normalized_response for bank in NOT_ACCEPTED_BANKS):
        await send_text_message(ws, "Lo sentimos, actualmente no estamos aceptando pagos de este banco. Estamos trabajando constantemente para expandir la lista de bancos aceptados. Gracias por elegirnos, que tenga un excelente día.", order_no)
        await add_to_blacklist(conn, buyer_name, order_no, None)
        return

    if normalized_response not in ['si', 'no']:
        await send_text_message(ws, "Para poder brindarle los datos bancarios, por favor responda exactamente con un 'Si' o 'No'.", order_no)
        await send_text_message(ws, questions[anti_fraud_stage], order_no)
        return

    fraud_responses = {(0, 'si'), (1, 'si')}
    deny_responses = {(2, 'no'), (4, 'no')}

    if (anti_fraud_stage, normalized_response) in fraud_responses:
        await send_text_message(ws, "Por razones de seguridad, no podemos continuar con este intercambio. Es posible que esté siendo víctima de un fraude. Por favor cancele la orden y no realice ninguna transferencia ya que puede perder su dinero.", order_no)
        await send_text_message(ws, transaction_denied, order_no)
        await add_to_blacklist(conn, buyer_name, order_no, None)
        return

    if (anti_fraud_stage, normalized_response) in deny_responses:
        await send_text_message(ws, "Por razones de seguridad, no podemos continuar con este intercambio. Gracias por su comprensión.", order_no)
        await add_to_blacklist(conn, buyer_name, order_no, None)
        return

    anti_fraud_stage += 1  # Proceed to the next stage
    await update_anti_fraud_stage(conn, buyer_name, anti_fraud_stage)

    if anti_fraud_stage == len(questions):
        await update_kyc_status(conn, buyer_name, 1)
        payment_details = await get_payment_details(conn, order_no)
        await send_text_message(ws, payment_warning, order_no)
        await send_text_message(ws, payment_details, order_no)
        await send_text_message(ws, payment_concept, order_no)
    else:
        await send_text_message(ws, questions[anti_fraud_stage], order_no)
