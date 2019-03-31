import logging


class Configuration:

    def __init__(self, options):
        self.options = options.params
        self.logger = self._init_logging()

    def _init_logging(self):
        # Set up logging
        loglevel = logging.INFO
        logger = logging.getLogger('webcrawler')
        logger.setLevel(loglevel)

        formatter = logging.Formatter('%(asctime)s - %(name)s(%(process)d) - %(levelname)s - %(funcName)s(): %(message)s')

        if self.options.writelog:
            fh = logging.FileHandler(self.options.writelog)
            fh.setLevel(loglevel)
            fh.setFormatter(formatter)
            logger.addHandler(fh)

        if not self.options.quiet:
            ch = logging.StreamHandler()
            ch.setLevel(loglevel)
            ch.setFormatter(formatter)
            logger.addHandler(ch)

        return logger
