"""This is the WebCrawler main entry point."""

from wclib.options import Options
from wclib.config import Configuration
from wclib.crawler import WebCrawler
from wclib.model import DataModelConfig

def launch_webcrawler():
    """ Actual point of execution for launching the web crawler."""
    options = Options().params
    config = Configuration(options)

    # Bootstrap the data model with the database
    DataModelConfig(config)

    # Bootstrap the web crawler with the configuration
    WebCrawler(config)


if __name__ == '__main__':
    launch_webcrawler()
