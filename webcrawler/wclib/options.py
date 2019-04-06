import argparse


class Options:

    def __init__(self):
        self.params = self._init_params()

    def _init_params(self):
        parser = argparse.ArgumentParser(description="WebCrawler - A rudimdentary website crawler.")

        parser.add_argument("-i", "--inifile", default="webcrawler.ini", help="Specify the configuration file containing database options and other parameters. [optional, default=webcrawler.ini]")
        parser.add_argument("-d", "--dbprofile", default="db-default", help="Specify the configuration section to read database configuration. [optional, default=db-default]")
        parser.add_argument("-p", "--processes", default=8, help="Specify the number of concurrent worker sub-processes. [optional, default=8]")
        parser.add_argument("-s", "--scan", required=True, help="Unique identifer of a new or existing scan job to run/continue running")
        parser.add_argument("-r", "--role", required=True, choices=['page', 'link'], help="Assign role to this invocation, either 'page' crawler or 'link' parser.")
        parser.add_argument("-l", "--loglevel", default="ERROR", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], help="Logging level - DEBUG|INFO|WARNING|ERROR|CRITICAL [optional, default=ERROR]")
        parser.add_argument("-w", "--writelog", nargs="?", const="webcrawler.log", help="Write log to a specified file [optional, default=webcrawler.log]")
        parser.add_argument("-q", "--quiet", action='store_const', const=True, help="Silence console logging [optional]")

        return parser.parse_args()
