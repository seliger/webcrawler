import logging
import configparser
import sys
import os

from . import model as dm

class Configuration:

    def __init__(self, options):
        self.options = options
        self.logger = self._init_logging()
        self.ini = self._init_inifile()
        self.dbname, self.dbconfig = self._init_dbconfig()
        self.mqueue = self._init_mqueueconfig()
        self.root_fqdns, self.blacklist, self.scan = self._init_scanconfig()
        self.httpconfig = self._init_httpconfig()
        self.sessionconfig = self._init_sessionconfig()

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

    def _init_scanconfig(self):

        # Bootstrap the database session
        dm.init(self)

        scan, created = dm.Scan.get_or_create(name=self.options.scan)

        root_fqdns = []
        for root in dm.ScanRoot.select().where(dm.ScanRoot.scan_id == scan.scan_id):
            if root.port:
                root_fqdns.append(root.fqdn + ":" + root.port)
            else:
                root_fqdns.append(root.fqdn)

        blacklist = {}
        for bl in dm.ScanBlacklist.select().where(dm.ScanBlacklist.scan_id == scan.scan_id):
            if not bl.fqdn in blacklist.keys():
                blacklist[bl.fqdn] = {}
            if not bl.path in blacklist[bl.fqdn] and not bl.path == None:
                if not 'path' in blacklist[bl.fqdn]:
                    blacklist[bl.fqdn]['path'] = []
                blacklist[bl.fqdn]['path'].append(bl.path)
            if not bl.netloc in blacklist[bl.fqdn] and not bl.netloc == None:
                if not 'netloc' in blacklist[bl.fqdn]:
                    blacklist[bl.fqdn]['netloc'] = []
                blacklist[bl.fqdn]['netloc'].append(bl.netloc)
            if not bl.scheme in blacklist[bl.fqdn] and not bl.scheme == None:
                if not 'scheme' in blacklist[bl.fqdn]:
                    blacklist[bl.fqdn]['scheme'] = []
                blacklist[bl.fqdn]['scheme'].append(bl.scheme)

        return (root_fqdns, blacklist, scan)

    def _init_mqueueconfig(self):
        if not 'mqueue' in self.ini.sections():
            self.logger.error("The ini file %s does not contain message queue configuration section 'mqueue'.", self.options.inifile)
            sys.exit(255)
        
        try:
            queue_config = {
                'host': self.ini['mqueue']['host'],
                'port': self.ini['mqueue']['port'],
                'user': self.ini['mqueue']['user'],
                'password': self.ini['mqueue']['password'],
                'vhost': self.ini['mqueue']['vhost']
            }
        except KeyError as ke:
            self.logger.error("Invalid configuration for profile %s. Configuration is missing %s.", 'mqueue', ke)
            sys.exit(255)

        return queue_config
        
    def _init_httpconfig(self):
        httpconfig = {}

        httpconfig['schemes'] = ['http', 'https']
        httpconfig['invalid_tokens'] = ['http[s]?://mailto:', 'mail to:']
        httpconfig['invalid_schemes'] = ['tel:', 'mailto:', 'mail to:']
        httpconfig['allowed_content_types'] = ['text/html', 'text/html; charset=UTF-8', 'text/html; charset=utf-8']

        return httpconfig

    def _init_sessionconfig(self):
        sessionconfig = { 'sessionopts': {}, 'headers': {} }

        sessionconfig['sessionopts']['max_redirects'] = 10

        sessionconfig['headers']['Upgrade-Insecure-Requests'] = "1"
        sessionconfig['headers']['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'
        sessionconfig['headers']['DNT'] = "1"
        sessionconfig['headers']['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
        sessionconfig['headers']['Accept-Encoding'] = 'gzip, deflate, br'
        sessionconfig['headers']['Accept-Language'] = 'en-US,en;q=0.9'
        sessionconfig['headers']['Range'] = 'bytes=0-1000000'

        return sessionconfig