"""This is the WebCrawler main entry point."""

from wclib.options import Options 
from wclib.config import Configuration
from wclib.crawler import WebCrawler


def launch_webcrawler():
    """ Actual point of execution for launching the web crawler."""
    options = Options().params
    config = Configuration(options)

    # Bootstrap the web crawler with the configuration
    crawler = WebCrawler(config)

    crawler.run(config.scan.seed_url)


if __name__ == '__main__':
    launch_webcrawler()
