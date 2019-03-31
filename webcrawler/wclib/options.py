import argparse


class Options:

    def __init__(self):
        self.params = self._init_params()

    def _init_params(self):
        parser = argparse.ArgumentParser(description="WebCrawler - A rudimdentary website crawler.")

        parser.add_argument("-s", "--scan", required=True, help="Unique identifer of a new or existing scan job to run/continue running")
        parser.add_argument("-l", "--loglevel", default="ERROR", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="Logging level - DEBUG|INFO|WARNING|ERROR|CRITICAL [optional, default=ERROR]")
        parser.add_argument("-w", "--writelog", nargs="?", const="webcrawler.log", help="Write log to a specified file [optional, default=webcrawler.log]")
        parser.add_argument("-q", "--quiet", action='store_const', const=True, help="Silence console logging [optional]")

        return parser.parse_args()
