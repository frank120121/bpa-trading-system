import asyncio
import logging
from fetch_emails import outlook_fetch_ip
from ip_info_io import get_ip_origin
logger = logging.getLogger(__name__)
async def fetch_ip(last_four_digits):
    ip = await outlook_fetch_ip(last_four_digits)
    return ip
async def main():
    last_four_digits = '4208'
    ip_address = await fetch_ip(last_four_digits)
    if ip_address:
        country = get_ip_origin(ip_address)
        if country != "MX":
            logger.warning(f"The IP address {ip_address} originates from outside of Mexico!")
        else:
            logger.info(f"The IP address {ip_address} is from Mexico.")
    else:
        logger.error(f"Could not fetch the IP address for the last four digits: {last_four_digits}")

if __name__ == "__main__":
    asyncio.run(main())