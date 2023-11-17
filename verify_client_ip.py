import asyncio
import logging
from fetch_outlook import outlook_fetch_ip
from fetch_gmail import gmail_fetch_ip
from ip_info_io import get_ip_origin
from common_vars import MERCHANTS
logger = logging.getLogger(__name__)
async def fetch_ip(last_four_digits, seller_name):
    if seller_name not in MERCHANTS:
        return
    email_id = MERCHANTS[seller_name]
    if email_id == 1:
        ip = await outlook_fetch_ip(last_four_digits)
    else:
        ip = await gmail_fetch_ip(last_four_digits)
    if ip:
        country = get_ip_origin(ip)
        return country
    else:
        logger.error(f"Could not fetch the IP address for the last four digits: {last_four_digits}")
        
async def main():
    last_four_digits = '5952'
    seller_name = 'GUERRERO LOPEZ MARTHA'
    country = await fetch_ip(last_four_digits, seller_name)
    if country and country != "MX":
        logger.warning(f"The IP address originates from outside of Mexico!")
    elif country == "MX":
        logger.info(f"The IP address is from Mexico.")

if __name__ == "__main__":
    asyncio.run(main())