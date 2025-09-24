# bpa/common/vars.py 
already_processed = set()
ProhibitedPaymentTypes = "TERCEROS, BANCOPPEL, BANCO AZTECA, STP, MERCADO PAGO, o en EFECTIVO"
ORDER_STATUS_UNDER_REVIEW = 2
FIAT_UNIT_MXN = 'MXN'
FIAT_UNIT_USD = 'USD'

MGL_SPOT = 1
MFM_SPOT = 1
MXN_BTC_AMT = 5000
MXN_USDT_AMT = 3000
USD_AMT_1 = 100
USD_AMT_2 = 500
MXN_SELL_AMT = 5000

MGL_SELL_AMT = 50000
MFM_SELL_AMT = 5000
MFM_SELL_AMT_MIN = 15000

MGL_BUY_MIN = 10000
MGL_BUY_MIN_2 = 2000
MGL_BUY_TRANS_AMT = 10000

MFM_BUY_MIN = 50000
MFM_BUY_MIN_2 = 2000
MFM_BUY_TRANS_AMT = 15000

ads_dict = {
    'account_1': [
        # SELL USD
        {'advNo': '13800974169104801792', 'target_spot': 1, 'asset_type': 'USDT', 'fiat': 'USD', 'transAmount': 200, 'payType': ['Zelle'], 'Group': '1', 'trade_type': 'BUY', 'minTransAmount': 100},
        # BUY MXN
        {'advNo': '13803221462884372480', 'target_spot': 1, 'asset_type': 'BTC', 'fiat': 'MXN', 'transAmount': 10000, 'payType': None, 'Group': '2', 'trade_type': 'BUY', 'minTransAmount': 10000},
        {'advNo': '13803221805828591616', 'target_spot': 1, 'asset_type': 'ETH', 'fiat': 'MXN', 'transAmount': 10000, 'payType': None, 'Group': '3', 'trade_type': 'BUY', 'minTransAmount': 10000},
        {'advNo': '13803602480206028800', 'target_spot': 1, 'asset_type': 'USDT', 'fiat': 'MXN', 'transAmount': 1000, 'payType': ['OXXO'], 'Group': '4', 'trade_type': 'BUY', 'minTransAmount': 10000},

        # BUY MXN
        {'advNo': '12800980734114803712', 'target_spot': 1, 'asset_type': 'BTC', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '1', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803238551064883200', 'target_spot': 1, 'asset_type': 'USDT', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '2', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803238770522886144', 'target_spot': 1, 'asset_type': 'BNB', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '3', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803239210472775680', 'target_spot': 1, 'asset_type': 'ETH', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '4', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803239799010684928', 'target_spot': 1, 'asset_type': 'DOGE', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '6', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803240765128060928', 'target_spot': 1, 'asset_type': 'ADA', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '7', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803240929168142336', 'target_spot': 1, 'asset_type': 'XRP', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '8', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803241148515414016', 'target_spot': 1, 'asset_type': 'FDUSD', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '9', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803241346739613696', 'target_spot': 1, 'asset_type': 'USDC', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '11', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803241582550941696', 'target_spot': 1, 'asset_type': 'WLD', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '12', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803241776176566272', 'target_spot': 1, 'asset_type': 'TRUMP', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '13', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803241969790197760', 'target_spot': 1, 'asset_type': 'TST', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '14', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},
        {'advNo': '12803242313186107392', 'target_spot': 1, 'asset_type': 'SOL', 'fiat': 'MXN', 'transAmount': MFM_SELL_AMT, 'payType': None, 'Group': '16', 'trade_type': 'SELL', 'minTransAmount': MFM_SELL_AMT_MIN},

    ],
    'account_2': [

    ]
}


status_map = {
    'seller_merchant_trading': 1,
    'seller_payed': 2,
    'buyer_merchant_trading': 3,
    'seller_completed': 4,
    'be_appeal': 5,
    'seller_cancelled': 6,
    'cancelled_by_system': 7,
    'buyer_payed': 8,
    'submit_appeal': 9
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
    'MUÑOZ PEREA MARIA FERNANDA': 1
}

MONTHLY_LIMITS = 2000000.00
DAILY_LIMITS = 150000.00
OXXO_MONTHLY_LIMIT = 800000.00


#Oxxo Limits
BBVA_OXXO_DAILY_LIMIT = 19000.00
BANAMEX_OXXO_DAILY_LIMIT = 18000.00
SANTANDER_OXXO_DAILY_LIMIT = 10000.00
SCOTIABANK_OXXO_DAILY_LIMIT = 17760.00
INBURSA_OXXO_DAILY_LIMIT = 24000.00
HSBC_OXXO_DAILY_LIMIT = 20000.00
CAJAPOPULAR_OXXO_DAILY_LIMIT = 20000.00
INVEX_OXXO_DAILY_LIMIT = 19000.00
BANREGIO_OXXO_DAILY_LIMIT = 30000.00
SPIN_OXXO_DAILY_LIMIT = 10000.00

#Oxxo Limits too low
AFIRME_OXXO_DAILY_LIMIT = 5000.00
BANCOPPEL_OXXO_DAILY_LIMIT = 5000.00

#Oxxo Monthly Limit
OXXO_MONTHLY_LIMIT = 80000.00
OXXO_DAILY_LIMIT = 10000.00


BANREGIO_OXXO_MONTHLY_LIMIT = 900000.00

#Zelle limits
ZELLE_MONTHLY_LIMIT = 1500.00
ZELLE_DAILY_LIMIT = 1000.00



payment_accounts = [
    # MXN Bank Accounts
    {"fiat": "MXN", "pay_type": "BBVA", "beneficiary": "FRANCISCO JAVIER LOPEZ GUERRERO", "account_details": "1532335128", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},
    {"fiat": "MXN", "pay_type": "BBVA", "beneficiary": "MARIA FERNANDA MUNOZ PEREA", "account_details": "1593999048", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},
    {"fiat": "MXN", "pay_type": "BBVA", "beneficiary": "MARIA FERNANDA MUNOZ PEREA", "account_details": "0482424657", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},
    {"fiat": "MXN", "pay_type": "BBVA", "beneficiary": "ANBER CAP DE MEXICO SA DE CV", "account_details": "0122819805", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},
    {"fiat": "MXN", "pay_type": "Nvio", "beneficiary": "FRANCISCO JAVIER LOPEZ GUERRERO", "account_details": "710969000007300927", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},
    {"fiat": "MXN", "pay_type": "Nvio", "beneficiary": "MARIA FERNANDA MUNOZ PEREA", "account_details": "710969000016348705", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},
    {"fiat": "MXN", "pay_type": "Nvio", "beneficiary": "MARTHA GUERRERO LOPEZ", "account_details": "710969000015306104", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},
    {"fiat": "MXN", "pay_type": "Santander", "beneficiary": "MARTHA GUERRERO LOPEZ", "account_details": "65509141646", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},
    {"fiat": "MXN", "pay_type": "STP", "beneficiary": "ANBER CAP DE MEXICO SA DE CV", "account_details": "646180204200033494", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},
    {"fiat": "MXN", "pay_type": "STP", "beneficiary": "FRANCISCO JAVIER LOPEZ GUERRERO", "account_details": "646180146099983826", "daily_limit": DAILY_LIMITS, "monthly_limit": MONTHLY_LIMITS},

    # OXXO Debit Cards
    {"fiat": "MXN", "pay_type": "OXXO", "beneficiary": "MARTHA GUERRERO LOPEZ", "account_details": "4347984837112696", "daily_limit": OXXO_DAILY_LIMIT, "monthly_limit": OXXO_MONTHLY_LIMIT},
    {"fiat": "MXN", "pay_type": "OXXO", "beneficiary": "MARTHA GUERRERO LOPEZ", "account_details": "4347984868505966", "daily_limit": OXXO_DAILY_LIMIT, "monthly_limit": OXXO_MONTHLY_LIMIT},
    {"fiat": "MXN", "pay_type": "OXXO", "beneficiary": "MARTHA GUERRERO LOPEZ", "account_details": "4347984866288631", "daily_limit": OXXO_DAILY_LIMIT, "monthly_limit": OXXO_MONTHLY_LIMIT},
    {"fiat": "MXN", "pay_type": "OXXO", "beneficiary": "MARTHA GUERRERO LOPEZ", "account_details": "2242170760065560", "daily_limit": OXXO_DAILY_LIMIT, "monthly_limit": OXXO_MONTHLY_LIMIT},
    {"fiat": "MXN", "pay_type": "OXXO", "beneficiary": "MARIA FERNANDA MUNOZ PEREA", "account_details": "2242170760324680", "daily_limit": OXXO_DAILY_LIMIT, "monthly_limit": OXXO_MONTHLY_LIMIT},
    {"fiat": "MXN", "pay_type": "OXXO", "beneficiary": "FRANCISCO JAVIER LOPEZ GUERRERO", "account_details": "2242170760314240", "daily_limit": OXXO_DAILY_LIMIT, "monthly_limit": OXXO_MONTHLY_LIMIT},

    # USD Zelle Accounts
    {"fiat": "USD", "pay_type": "Zelle", "beneficiary": "Francisco Javier Lopez", "account_details": "5202276042", "daily_limit": ZELLE_DAILY_LIMIT, "monthly_limit": 2500},
    {"fiat": "USD", "pay_type": "Zelle", "beneficiary": "Francisco Javier Lopez", "account_details": "Francisco.lopez4256@gmail.com", "daily_limit": ZELLE_DAILY_LIMIT, "monthly_limit": 2500},
    {"fiat": "USD", "pay_type": "Zelle", "beneficiary": "Francisco Javier Lopez", "account_details": "Franciscoj.lopez1201@gmail.com", "daily_limit": ZELLE_DAILY_LIMIT, "monthly_limit": 2500},
]


NOT_ACCEPTED_BANKS = {"banco azteca", "mercado pago", "stp", "bancoppel", "albo", "azteca", "mercadopago", "coppel"}

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
    'tesored', 'transfer', 'unagra', 'valmex', 'value', 've por mas', 'vector', 'spin', 'citibanamex'
}

BBVA_BANKS = ['bbva', 'bbva bancomer', 'bancomer', 'bbva mexico']

def normalize_bank_name(bank_name: str) -> str:
    """Normalizes bank names for consistent lookup"""
    if not bank_name:
        return bank_name
    
    bank_name = bank_name.lower().strip()
    
    # Direct match with SPEI codes
    if bank_name in BANK_SPEI_CODES:
        return bank_name

    # Common variations
    bank_mappings = {
        'bbva': ['bancomer', 'bbva bancomer', 'bbva mexico'],
        'nu': ['nu bank', 'nu mexico', 'nubank'],
        'banamex': ['citibanamex'],
        'scotiabank': ['scotia'],
    }

    # Check if the bank name is a variation of a standard name
    for standard_name, variations in bank_mappings.items():
        if bank_name in variations or any(var in bank_name for var in variations):
            return standard_name

    # If no specific mapping found, return the original name
    return bank_name

CUTOFF_DAYS = 1

prohibited_countries = [
    "AF", "AL", "AZ", "BY", "BZ", "BA", "BI", "CF", "TD", "CD", "CU", "CY", "ET", "GY",
    "HT", "HN", "IR", "IQ", "XK", "KG", "LA", "LB", "LY", "MK", "ML", "ME", "MZ", "MM",
    "NI", "NG", "KP", "PG", "PY", "PK", "PA", "ST", "RS", "SO", "SS", "SD", "SY",
    "TZ", "TJ", "TT", "TR", "TM", "UA", "UZ", "VU", "YE", "ZW"
]

prohibited_countries_v2 = [
    "AF", "BY", "BI", "TD", "CD", "KP", "CU", "ER", "IQ", "IR", "LY", "MM", "CF", "SS", "RU", "SY", "SO", "SD", "YE", "VE", "UA"
]

ACCEPTED_COUNTRIES_FOR_OXXO = ['MX', 'CO', 'VE', 'AR', 'ES', 'CL', 'CA', 'HK', 'PE', 'BE', 'EC', 'RU', 'TH', 'IN', 'UA', 'DE', 'JP', 'US', 'RU', 'FR']

BANK_SPEI_CODES = {
    # Most common banks from our analysis
    'nvio': '90710',
    'bbva': '40012',
    'bbva mexico': '40012',
    'bancomer': '40012',
    'bbva bancomer': '40012',
    'banorte': '40072',
    'santander': '40014',
    'banamex': '40002',
    'hsbc': '40021',
    'scotiabank': '40044',
    'nu': '90638',
    'nu mexico': '90638',
    'transfer': '90656',
    'inbursa': '40036',
    'banregio': '40058',
    'bajio': '40030',
    'actinver': '40133',
    
    # Additional major banks from Banxico list that might appear
    'azteca': '40127',
    'bancoppel': '40137',
    'afirme': '40062',
    'compartamos': '40130',
    'mifel': '40042',
    'multiva': '40132',
    'bmonex': '40112',
    'cibanco': '40143',
    'jpmorgan': '40110',
    've por mas': '40113',
    
    # Digital/Fintech banks that are common in crypto
    'spin by oxxo': '90728',
    'mercado pago': '90722',
    'klar': '90661',
}