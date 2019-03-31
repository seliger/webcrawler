"""This is the WebCrawler main entry point."""

from wclib.options import Options
from wclib.config import Configuration


def launch_webcrawler():
    """ Actual point of execution for launching the web crawler."""
    options = Options()
    config = Configuration(options)

    config.logger.error("Test")


if __name__ == '__main__':
    launch_webcrawler()
