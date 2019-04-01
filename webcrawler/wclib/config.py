import logging
import configparser
import sys
import os

class Configuration:

    def __init__(self, options):
        self.options = options
        self.logger = self._init_logging()
        self.ini = self._init_inifile()
        self.dbname, self.dbconfig = self._init_dbconfig()

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

    def _init_inifile(self):

        if not os.path.exists(self.options.inifile):
            self.logger.error("The ini file %s does not exist, cannot continue.", self.options.inifile)
            sys.exit(255)

        config = configparser.ConfigParser()
        config.read(self.options.inifile)

        if len(config.sections()) == 0:
            self.logger.error("The ini file %s does not have any sections.", self.options.inifile)
            sys.exit(255)

        return config

    def _init_dbconfig(self):

        if not self.options.dbprofile in self.ini.sections():
            self.logger.error("The ini file %s does not contain database configuration section %s.", self.options.inifile, self.options.dbprofile)
            sys.exit(255)
        
        try:
            db_name = self.ini[self.options.dbprofile]['dbname']
            db_config = {
                'charset': 'utf8', 
                'use_unicode': True, 
                'host': self.ini[self.options.dbprofile]['host'], 
                'user': self.ini[self.options.dbprofile]['user'], 
                'password': self.ini[self.options.dbprofile]['password']
            }
        except KeyError as ke:
            self.logger.error("Invalid configuration for profile %s. Configuration is missing %s.", self.options.dbprofile, ke)
            sys.exit(255)

        return (db_name, db_config)

