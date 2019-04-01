from .model import *


class WebCrawler:

    def __init__(self, config):
        self.config = config
        self.logger = config.logger

        self.logger.debug("Hello from webcrawler... Starting up.")

        scan, created = Scan.get_or_create(name=self.config.options.scan)

        self.logger.debug("The seed URL is %s.", scan.seed_url)