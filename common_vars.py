already_processed = set()
ProhibitedPaymentTypes = "TERCEROS, BANCOPPEL, BANCO AZTECA, STP, MERCADO PAGO, o en EFECTIVO"
ORDER_STATUS_UNDER_REVIEW = 2
FIAT_UNIT_MXN = 'MXN'
FIAT_UNIT_USD = 'USD'
MGL_SPOT = 1
MFM_SPOT = 2
MXN_BTC_AMT = '5000'
MXN_USDT_AMT = '30000'
USD_AMT_1 = '100'
USD_AMT_2 = '500'



ads_dict = {
    'account_1': [
        {'advNo': '11531824717949116416', 'target_spot': MFM_SPOT, 'asset_type': 'BTC', 'fiat': 'MXN', 'transAmount':MXN_BTC_AMT, 'payTypes': None, 'Group': '1'},
        {'advNo': '11515582400296718336', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'MXN', 'transAmount':MXN_USDT_AMT, 'payTypes': ['BBVABank'], 'Group': '2'},
        # {'advNo': '12578447747234050048', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_1, 'payTypes': ['Zelle'], 'Group': '3'},
        # {'advNo': '12590565226093010944', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_2, 'payTypes': ['Zelle'], 'Group': '4'},
        # {'advNo': '12590566284535308288', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_1, 'payTypes': ['SkrillMoneybookers'], 'Group': '5'},
        # {'advNo': '12590567548383592448', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_2, 'payTypes': ['SkrillMoneybookers'], 'Group': '6'},
        # {'advNo': '12590568032956669952', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_1, 'payTypes': ['BANK'], 'Group': '7'},
        # {'advNo': '12590568277293666304', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_2, 'payTypes': ['BANK'], 'Group': '8'}
    ],
    'account_2': [
        {'advNo': '12590489123493851136', 'target_spot': MGL_SPOT, 'asset_type': 'BTC', 'fiat': 'MXN', 'transAmount':MXN_BTC_AMT, 'payTypes': None, 'Group': '1'},
        {'advNo': '12590488417885061120', 'target_spot': MGL_SPOT, 'asset_type': 'USDT', 'fiat': 'MXN', 'transAmount':MXN_USDT_AMT, 'payTypes': ['BBVABank'], 'Group': '2'},
    #     {'advNo': '12590585293541416960', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_1, 'payTypes': ['Zelle'], 'Group': '3'},
    #     {'advNo': '12590585457789411328', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_2, 'payTypes': ['Zelle'], 'Group': '4'},
    #     {'advNo': '12590585929304309760', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_1, 'payTypes': ['SkrillMoneybookers'], 'Group': '5'},
    #     {'advNo': '12590586117778108416', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_2, 'payTypes': ['SkrillMoneybookers'], 'Group': '6'},
    #     {'advNo': '12590586776166993920', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_1, 'payTypes': ['BANK'], 'Group': '7'},
    #     {'advNo': '12590586951200821248', 'target_spot': MFM_SPOT, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount':USD_AMT_2, 'payTypes': ['BANK'], 'Group': '8'}
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

temp_ignore = {
    'seller_merchant_trading': 1,
    'seller_payed': 2,
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
        "limit": 95000.00
    },
    {
        "bank_name": "STP",
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
        "account_number": "012778015939990486",
        "limit": 95000.00
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
        "account_number": "012778004824246573",
        "limit": 95000.00
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
    },
    {
        "bank_name": "STP",
        "beneficiary": "ANBER CAP DE MEXICO SA DE CV",
        "account_number": "646180204200033494",
        "limit": 90000.00
    }
]

NOT_ACCEPTED_BANKS = {"banco azteca", "mercado pago", "stp", "bancoppel", "albo", "azteca", "mercadopago", "oxxo", "coppel"}

ACCEPTED_BANKS = {
    'abc capital', 'actinver', 'afirme', 'alternativos', 'arcus', 'asp integra opc',
    'autofin', 'babien', 'bajio', 'banamex', 'banco covalto', 'banco s3', 'bancomer',
    'bancomext', 'bancrea', 'banjercito', 'bankaool', 'banobras', 'banorte',
    'banregio', 'bansi', 'banxico', 'barclays', 'bbase', 'bbva', 'bbva bancomer',
    'bbva mexico', 'bmonex', 'caja pop mexica', 'cb intercam', 'cibanco', 'compartamos',
    'consubanco', 'cuenca', 'donde', 'finamex', 'gbm', 'hsbc', 'icbc', 'inbursa',
    'indeval', 'intercam banco', 'invercap', 'invex', 'kuspit', 'libertad', 'masari',
    'mifel', 'monex', 'multiva banco', 'nafin', 'nu', 'nu bank', 'nu mexico', 'nvio',
    'pagatodo', 'profuturo', 'sabadell', 'santander', 'scotia', 'scotiabank', 'shinhan',
    'tesored', 'transfer', 'unagra', 'valmex', 'value', 've por mas', 'vector', 'spin'
}

BBVA_BANKS = ['bbva', 'bbva bancomer', 'bancomer', 'bbva mexico']
CUTOFF_DAYS = 1

DB_FILE = 'C:/Users/p7016/Documents/bpa/orders_data.db'

prohibited_countries = [
    "AF", "AL", "AZ", "BY", "BZ", "BA", "BI", "CF", "TD", "CD", "CU", "CY", "ET", "GY",
    "HT", "HN", "IR", "IQ", "XK", "KG", "LA", "LB", "LY", "MK", "ML", "ME", "MZ", "MM",
    "NI", "NG", "KP", "PG", "PY", "PK", "PA", "ST", "RS", "SO", "SS", "SD", "SY",
    "TZ", "TJ", "TT", "TR", "TM", "UA", "UZ", "VU", "YE", "ZW"
]