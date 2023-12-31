from database import update_anti_fraud_stage, update_kyc_status
from binance_messages import send_text_message
from binance_blacklist import add_to_blacklist
from lang_utils import transaction_denied, payment_concept, payment_warning
from binance_bank_deposit import get_payment_details

async def handle_anti_fraud(buyer_name, conn, anti_fraud_stage, response, order_no, ws):
    def get_next_question(stage):
        questions = [
            "¿Le han ofrecido un trabajo, una oportunidad de inversión o una gran oferta que requiere invertir a través de Bitcoin, USDT, o alguna criptomoneda?(1/3)",
            "¿Alguien lo/la está presionando para realizar el pago?(2/3)",
            "¿Está de acuerdo que las transacciones con este tipo de activos son irreversibles y que, una vez enviados, no hay manera de recuperarlos?(3/3)",
            f"¿La cuenta bancaria que utilizara para realizar el pago esta a su nombre?({buyer_name})",
            """¿El banco que utilizara para realizar el pago es alguno de los siguientes?:

        Banco Azteca
        Mercado Pago
        STP
        OXXO Spin
        BanCoppel"""
        ]
        return questions[stage] if 0 <= stage < len(questions) else None

    normalized_response = response.strip().lower()
    if normalized_response not in ['si', 'no', 'start_pro']:
        await send_text_message(ws, "Para poder brindarle los datos bancarios, por favor responda exactamente con un Si o No.", order_no)
        prev_question = get_next_question(anti_fraud_stage)
        if prev_question:
            await send_text_message(ws, prev_question, order_no)
        return

    fraud_response_conditions = {
        (0, 'si'), (1, 'si'), (4, 'si'),
        (2, 'no'), (3, 'no')
    }
    if (anti_fraud_stage, normalized_response) in fraud_response_conditions:
        await send_text_message(ws, "Por razones de seguridad, no podemos continuar con este intercambio. Es posible que este siendo víctima de un fraude. Por favor cancele la orden y no realice ninguna transferencia ya que puede perder su dinero.", order_no)
        await send_text_message(ws, transaction_denied, order_no)
        await add_to_blacklist(conn, buyer_name, order_no, None)
        return

    # Update and check the stage
    if normalized_response == 'no' and anti_fraud_stage in [0, 1, 4]:
        anti_fraud_stage += 1
    elif normalized_response == 'si' and anti_fraud_stage in [2, 3]:
        anti_fraud_stage += 1

    await update_anti_fraud_stage(conn, buyer_name, anti_fraud_stage)

    if anti_fraud_stage == 5:
        await update_kyc_status(conn, buyer_name, 1)
        payment_details = await get_payment_details(conn, order_no)
        await send_text_message(ws, payment_warning, order_no)
        await send_text_message(ws, payment_details, order_no)
        await send_text_message(ws, payment_concept, order_no)
    elif 0 <= anti_fraud_stage < 5:
        next_question = get_next_question(anti_fraud_stage)
        await send_text_message(ws, next_question, order_no)
