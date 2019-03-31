import logging


class Configuration:

    def __init__(self, options):
        self.options = options
        self.logger = self._init_logging()

    def _init_logging(self):
        # Set up logging
        logger = logging.getLogger('webcrawler')

        # Map the text log levels to the actual levels and set
        loglevels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
            }
        logger.setLevel(loglevels[self.options.loglevel])

        formatter = logging.Formatter('%(asctime)s - %(name)s(%(process)d) - %(levelname)s - %(module)s - %(funcName)s(): %(message)s')

        if self.options.writelog:
            fh = logging.FileHandler(self.options.writelog)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

        if not self.options.quiet:
            ch = logging.StreamHandler()
            ch.setFormatter(formatter)
            logger.addHandler(ch)

        return logger
