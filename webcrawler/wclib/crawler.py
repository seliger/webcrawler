class WebCrawler:

    def __init__(self, config):
        self.config = config
        self.logger = config.logger

        self.logger.debug("Hello from webcrawler... Starting up.")