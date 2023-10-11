already_processed = set()
ProhibitedPaymentTypes = "TERCEROS, BANCO AZTECA, STP, MERCADO PAGO, o en Efectivo"
ORDER_STATUS_UNDER_REVIEW = 2
FIAT_UNIT_MXN = 'MXN'
FIAT_UNIT_USD = 'USD'

ads_dict = {
    'account_1': [
        {'advNo': '11531824717949116416', 'target_spot': 2, 'asset_type': 'BTC'},
        {'advNo': '11515582400296718336', 'target_spot': 1, 'asset_type': 'USDT'}
    ],
    'account_2': [
        {'advNo': '11531141756952866816', 'target_spot': 1, 'asset_type': 'BTC'},
        {'advNo': '11519225605560729600', 'target_spot': 2, 'asset_type': 'USDT'}
    ]
}