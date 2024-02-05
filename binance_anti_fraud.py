from fuzzywuzzy import process
from database import update_anti_fraud_stage, update_kyc_status
from binance_messages import send_text_message
from binance_blacklist import add_to_blacklist
from lang_utils import transaction_denied, payment_concept, payment_warning
from binance_bank_deposit import get_payment_details
from common_vars import NOT_ACCEPTED_BANKS, ACCEPTED_BANKS
from database import update_buyer_bank

async def handle_anti_fraud(buyer_name, seller_name, conn, anti_fraud_stage, response, order_no, ws):
    questions = [
        f"¿Le han ofrecido un trabajo, una oportunidad de inversión o una gran oferta que requiere invertir a través de Bitcoin, USDT, o alguna criptomoneda? (1/3)",
        "¿Alguien lo/la está presionando para realizar el pago? (2/3)",
        f"¿Está de acuerdo que este es solo una orden de compra entre usted y el vendedor, y que además el vendedor no será responsable de ninguna devolución una vez completado la orden con éxito? (3/3)",
        "Muchas gracias por completar las preguntas, ahora para brindarle un servicio más eficiente, ¿podría indicarnos el nombre del banco que utilizará para realizar el pago?",
        f"Por ultimo, la cuenta bancaria que utilizará para realizar el pago, ¿está a su nombre? ({buyer_name})",
    ]

    # Check if the special "start_pro" command is given to start the process
    if response == "start_pro":
        anti_fraud_stage = 0
        await send_text_message(ws, questions[anti_fraud_stage], order_no)  # Send the first question immediately
        return  # Exit the function to avoid further processing

    normalized_response = response.strip().lower()
    if anti_fraud_stage >= len(questions):
        return  # No more questions

    if anti_fraud_stage == 3:
        # Direct match for not accepted banks
        if normalized_response in [bank.lower() for bank in NOT_ACCEPTED_BANKS]:
            await send_text_message(ws, "Lo sentimos, actualmente no estamos aceptando pagos de este banco. Estamos trabajando constantemente para expandir la lista de bancos aceptados. Gracias por elegirnos, que tenga un excelente día.", order_no)
            await add_to_blacklist(conn, buyer_name, order_no, None)
            return

        # Fuzzy matching for accepted banks
        closest_match, similarity = process.extractOne(normalized_response, [bank.lower() for bank in ACCEPTED_BANKS])
        if similarity >= 80:  # Threshold of 80%
            await update_buyer_bank(conn, order_no, closest_match)  # Use the closest match
        else:
            accepted_banks_list = ', '.join(ACCEPTED_BANKS)
            await send_text_message(ws, f"No pudimos verificar el banco proporcionado. Por favor, asegúrese de elegir uno de los siguientes bancos aceptados: {accepted_banks_list}", order_no)
            await send_text_message(ws, questions[3], order_no)  # Ask the bank question again
            return
        
    if anti_fraud_stage in [0, 1, 2, 4] and normalized_response not in ['si', 'no']:
        await send_text_message(ws, "Para poder brindarle los datos bancarios, por favor responda exactamente con un 'Si' o un 'No'.", order_no)
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
