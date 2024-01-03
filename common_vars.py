already_processed = set()
ProhibitedPaymentTypes = "TERCEROS, BANCOPPEL, BANCO AZTECA, STP, MERCADO PAGO, o en EFECTIVO"
ORDER_STATUS_UNDER_REVIEW = 2
FIAT_UNIT_MXN = 'MXN'
FIAT_UNIT_USD = 'USD'

ads_dict = {
    'account_1': [
        {'advNo': '11531824717949116416', 'target_spot': 1, 'asset_type': 'BTC'},
        {'advNo': '11515582400296718336', 'target_spot': 1, 'asset_type': 'USDT'}
    ],
    'account_2': [
        {'advNo': '11531141756952866816', 'target_spot': 2, 'asset_type': 'BTC'},
        {'advNo': '11519225605560729600', 'target_spot': 2, 'asset_type': 'USDT'}
    ]
}

status_map = {
    'buyer_merchant_trading': 3,
    'seller_merchant_trading': 1,
    'seller_payed': 2,
    'buyer_payed': 8,
    'submit_appeal': 9,
    'be_appeal': 5,
    'seller_completed': 4,
    'seller_cancelled': 6,
    'cancelled_by_system': 7
}


SYSTEM_REPLY_FUNCTIONS = {
    1: 'new_order',
    2: 'request_proof',
    3: 'we_are_buying',
    4: 'completed_order',
    5: 'customer_appealed',
    6: 'seller_cancelled',
    7: 'canceled_by_system',
    8: 'we_payed',
    9: 'we_apealed'
}

ANTI_FRAUD_CHECKS = {}

MERCHANTS = {
    'GUERRERO LOPEZ MARTHA': 2, 
    'MUNOZ PEREA MARIA FERNANDA': 1
}

bank_accounts = [
    {
        "bank_name": "Nvio",
        "beneficiary": "Francisco Javier Lopez",
        "account_number": "710969000007300927",
        "limit": 90000.00
    },
    {
        "bank_name": "BBVA",
        "beneficiary": "Francisco Javier Lopez",
        "account_number": "012778015323351288",
        "limit": 90000.00
    },
    {
        "bank_name": "Albo",
        "beneficiary": "Francisco Javier Lopez",
        "account_number": "646180146006124571",
        "limit": 90000.00
    },
    {
        "bank_name": "Banregio",
        "beneficiary": "Francisco Javier Lopez",
        "account_number": "058597000056476091",
        "limit": 90000.00
    },
    {
        "bank_name": "BBVA",
        "beneficiary": "Maria Fernanda Munoz Perea",
        "account_number": "012778004824246573",
        "limit": 90000.00
    },
    {
        "bank_name": "Nvio",
        "beneficiary": "Maria Fernanda Munoz Perea",
        "account_number": "710969000016348705",
        "limit": 90000.00
    },
    {
        "bank_name": "BBVA",
        "beneficiary": "Maria Fernanda Munoz Perea",
        "account_number": "012778015939990486",
        "limit": 90000.00
    },
    {
        "bank_name": "Nvio",
        "beneficiary": "Martha Guerrero Lopez",
        "account_number": "710969000015306104",
        "limit": 90000.00
    },
    {
        "bank_name": "Banregio",
        "beneficiary": "Martha Guerrero Lopez",
        "account_number": "058597000054265356",
        "limit": 90000.00
    },
    {
        "bank_name": "Santander",
        "beneficiary": "Martha Guerrero Lopez",
        "account_number": "014761655091416464",
        "limit": 90000.00
    }
]
