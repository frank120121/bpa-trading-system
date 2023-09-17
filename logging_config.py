import logging.config
def setup_logging():
    logging.basicConfig(filename='database.log', level=logging.DEBUG,
                        format='%(asctime)s:%(levelname)s:%(message)s')


if __name__ == '__main__':
    setup_logging()