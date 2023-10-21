import ipinfo
import logging
logger = logging.getLogger(__name__)
def get_ip_origin(ip_address):
    logger.info(f"Getting IP details for: {ip_address}")
    access_token = '51a4ceb0f429f2'
    handler = ipinfo.getHandler(access_token)
    details = handler.getDetails(ip_address)
    logger.info(f"Got IP details: {details}")
    return details.country



# access_token = '51a4ceb0f429f2'  # You get this when you sign up for ipinfo.io
# handler = ipinfo.getHandler(access_token)
# ip_address = "200.68.166.226"  # You can replace this with any valid IP address
# details = handler.getDetails(ip_address)

# print(details.all)
