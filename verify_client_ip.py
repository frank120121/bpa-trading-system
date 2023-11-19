import asyncio
import logging
from fetch_outlook import outlook_fetch_ip
from fetch_gmail import gmail_fetch_ip
from ip_info_io import get_ip_origin
from common_vars import MERCHANTS
logger = logging.getLogger(__name__)
async def fetch_ip(last_four_digits, seller_name):
    if seller_name not in MERCHANTS:
        logger.error(f"Seller not in MERCHANTS.")
        return
    email_id = MERCHANTS[seller_name]
    if email_id == 1:
        logger.info(f"Fetching from outlook.com")
        ip = await outlook_fetch_ip(last_four_digits)
    else:
        logger.info(f"Fetching from gmail.com")
        ip = await gmail_fetch_ip(last_four_digits)
    if ip:
        logger.info(f"IP is: {ip}")
        country = get_ip_origin(ip)
        logger.info(f"IP from Country: {country}")
        return country
    else:
        logger.error(f"Could not fetch the IP address for the last four digits: {last_four_digits}.")
        
async def main():
    last_four_digits = '3104'
    seller_name = 'MUNOZ PEREA MARIA FERNANDA'
    country = await fetch_ip(last_four_digits, seller_name)
    if country and country != "MX":
        logger.warning(f"The IP address originates from outside of Mexico!")
    elif country == "MX":
        logger.info(f"The IP address is from Mexico.")

if __name__ == "__main__":
    asyncio.run(main())