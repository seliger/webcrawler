from . import model as dm
from .mqueue import MessageQueue

from urllib.parse import urlparse, urlunparse
from bs4 import BeautifulSoup
from multiprocessing import Process

from playhouse.shortcuts import model_to_dict

import sys
import hashlib
import json
import re
import posixpath
import traceback
import urllib3
import requests
import datetime
import pika

class WebCrawler:

    def __init__(self, config):
        self.config = config
        self.logger = config.logger
        self.scan = config.scan

        self.logger.debug("Hello from webcrawler... Starting up.")

        # Fugly workaround to stop SSL errors (not checking for valid certs...)
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

        # Not sure this is needed here, but likely so with multiprocessing
        # Bootstrap the database connection for the data model
        dm.init(config)

        # Not sure if this is best here, but we'll go with it for now
        self.path_match = re.compile('^/([^/]+)/?')
        self.sub_path_match = re.compile(self.scan.sub_path_re)
        self.fp_match = re.compile('^(.*[/])')
        self.search_fqdn = self.scan.search_fqdn_re

    # def __del__(self):
    #     self.mq.destroy_queue(self.config.mqueue['queue_name'])

    def run(self, url):

        processes = []

        # Start up both queues
        self._config_mqueue('page')
        self._config_mqueue('link')


        if self.mq.queue_length(self.config.mqueue['queues']['page']) == 0:
            self.mq.queue_push(self.config.mqueue['queues']['page'], url)
                
        # Start up a set of crawler sub processes
        self.logger.debug("Instantiating %s worker processes.", self.config.options.processes)
        for p in range(int(self.config.options.processes)):
            self.logger.debug("Instantiating the worker process %s.", str(p+1))
            processes.append(Process(target=self._init_crawl_thread, args=(p+1,)))

        # Start the processes
        [x.start() for x in processes]

    def _config_mqueue(self, queue_name):
        # Configure the message queue name
        self.config.mqueue['queues'][queue_name] = self.config.scan.name + "_" + queue_name + "_queue"

        # Bootstrap the interface to the message queue
        self.mq = MessageQueue(self.config)
        self.mq.create_queue(self.config.mqueue['queues'][queue_name])

    def _mqueue_page_callback(self, ch, method, properties, body):
        self.logger.debug("In the callback, calling to crawl_page for url %s.", body.decode())
        self.crawl_page(urlparse(body.decode()))
    
        self.logger.debug("Acknowledging the receipt of url %s", body.decode())
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def _mqueue_link_callback(self, ch, method, properties, body):
        link_payload = json.loads(body.decode())
        self.logger.debug("In the callback, calling to crawl_page for url %s.", link_payload['url'])
        self.crawl_links(links=[urlparse(x) for x in link_payload['links']], url=urlparse(link_payload['url']))
    
        self.logger.debug("Acknowledging the receipt of url %s", body.decode())
        ch.basic_ack(delivery_tag=method.delivery_tag)

    def _init_crawl_thread(self, id):

        dm.init(self.config)

        while(True):
            try:                
                # Bootstrap the interface to the message queue
                self.mq = MessageQueue(self.config)

                # Start up both queues
                self._config_mqueue('page')
                self._config_mqueue('link')

                self.logger.info('Instantiated new crawler sub process %s for queue %s...', str(id), self.config.options.role)

                if self.config.options.role == 'page':
                    target_callback = self._mqueue_page_callback
                else:
                    target_callback = self._mqueue_link_callback
                    
                # Start listening for the specified queue role
                try:
                    self.mq.queue_consume(self.config.mqueue['queues'][self.config.options.role], target_callback)
                except KeyboardInterrupt:
                    self.mq.queue_stop_consuming(self.config.mqueue['queues'][self.config.options.role])
                    self.mq.destroy_conn()
                    break
            except pika.exceptions.ConnectionClosedByBroker:
                continue
            except pika.exceptions.AMQPChannelError as err:
                self.logger.error("Caught a channel error: %s, stopping...", err)
                break
            except pika.exceptions.AMQPConnectionError:
                print("Connection was closed, retrying...")
                continue

    def resolveComponents(self, url):
        orig_url = url
        if url.path:
            url = url._replace(path=posixpath.normpath(url.path))

        self.logger.debug("resolveComponents(): OLD PATH: " + orig_url.path + " NEW PATH: " + url.path)
        return url

    def instantiate_url(self, url):

        hashed_url = hashlib.sha256(url.geturl().encode()).hexdigest()

        (found_url, created) = dm.FoundURL.get_or_create(scan_id=self.scan.scan_id, url_hash=hashed_url)

        if created:
            self.logger.debug("URL '%s' was NOT FOUND in the database, creating...", url.geturl())
            found_url.scan_id = self.scan.scan_id
            found_url.url_hash = hashed_url
            found_url.url_text = url.geturl()
            found_url.is_crawled = False
            found_url.is_blacaklisted = False
            found_url.redirect_parent_url_id = None
            found_url.status_code = None
            found_url.content_type = None
            found_url.page_title = None
            found_url.root_stem = None
            found_url.hostname = url.hostname
            found_url.created_timestamp = datetime.datetime.now()
            found_url.crawled_timestamp = None
            found_url.is_new = True
            
            self.logger.debug("Saving new URL '%s'... with scan_id of %s and url_id of %s.", found_url.url_text, str(found_url.scan_id), str(found_url.url_id))
            found_url.save()
        else:
            found_url.is_new = False
            self.logger.debug("URL '%s' (%s) FOUND in the database, returning...", found_url.url_text, str(found_url.url_id))
    

        return found_url

    def log_url(self, url=None, record=None, backlink=None, pagelinks=None, content_type=None, status_code=None, error=None, is_blacklisted=False, redirect_parent=None, is_crawled=False):
        self.logger.debug("Entering log_url() for URL %s.", url.geturl())

        if record:
            found_url = record
        else:
            found_url = self.instantiate_url(url)

        # For grouping purposes, add the FQDN (or a fqdn/something)
        if not found_url.root_stem and url.hostname in self.config.root_fqdns and self.path_match.match(url.path):
            found_url.root_stem = url.hostname + self.path_match.match(url.path).group(0)
        else:
            found_url.root_stem = url.hostname

        # If this is a redirect, log its parent so we can retrace later
        if redirect_parent:
            # Go look up (or create) the identifier for the backlinked URL
            redirect = self.instantiate_url(redirect_parent)

            # Associate the redirect page ID to the URL
            found_url.redirect_parent_url_id = redirect.url_id

        # If backlink is None, that means we are logging an actual page crawl.
        if backlink is None:
            self.logger.debug("Logging that " + url.geturl() + " has been crawled.")

            # Set the status
            found_url.is_crawled = True

            # Set the crawled timestamp
            found_url.created_timestamp = datetime.datetime.now()

            if pagelinks and dm.PageLink.select().where(dm.PageLink.url_id == found_url.url_id).count() == 0:
                pagelinks_set = [{'url_id': found_url.url_id, 'link': z} for z in pagelinks]
                dm.PageLink.insert_many(pagelinks_set).execute()

            # Attach the HTTP status code and content type for the is_crawled web page.
            found_url.status_code = status_code
            found_url.content_type = content_type
            found_url.is_blacklisted = is_blacklisted

        # If backlink contains a value, that means we are writing a backlink to a different URL.
        else:
            self.logger.debug("Logging that URL %s backlinks to %s", url.geturl(), backlink.geturl())

            # Go look up (or create) the identifier for the backlinked URL
            backlink_instance = self.instantiate_url(backlink)

            dm.Backlink.create(**{
                'url_id': found_url.url_id,
                'backlink_url_id': backlink_instance.url_id,
                'backlink_timestamp': datetime.datetime.now()
            })

            if is_crawled:
                found_url.is_crawled = True
                found_url.crawled_timestamp = datetime.datetime.now()

        # Attempt to capture the error and force the page is_crawled.
        if error:
            found_url.is_crawled = True
            found_url.crawled_timestamp = datetime.datetime.now()
            dm.ScanError.create(**{
                'url_id': found_url.url_id,
                'error_text': error
            })

        # Write the instance back to the database
        found_url.save()

        # Throw it on the pile to be crawled later.
        if not found_url.is_crawled and found_url.is_new:
            self.mq.queue_push(self.config.mqueue['queues']['page'], url.geturl())

        return found_url.is_crawled

    def crawl_links(self, links=None, url=None):

        self.logger.info("Crawling links from URL: %s", url.geturl())
        # Scrape all of the links in the document and try to crawl them
        glob_uri = None
        for uri in links:
            glob_uri = uri
            try:
                self.logger.debug("Crawling link <" + str(uri.geturl()) + "> for parent URL " + str(url.geturl()))

                if uri.netloc or (not uri.netloc and uri.path):
                    self.logger.debug(uri.geturl() + " has a netloc and matches search_fqdn OR no netloc and a path.")

                    # 0 - scheme
                    # 1 - netloc
                    # 2 - path
                    # 3 - params
                    # 4 - query
                    # 5 - fragment (#)
                    uri_parts = list(uri)

                    # If we have a scheme, make sure it's one we care about
                    if uri.scheme and uri.scheme not in self.config.httpconfig['schemes']:
                        self.logger.debug("Not a valid scheme, skipping: " + uri.geturl())
                        continue

                    # If we have a scheme embedded at the start of the path, something is wrong.
                    if (not uri.scheme and uri.path) and any([re.search("^" + x, uri.path) for x in self.config.httpconfig['invalid_schemes']]):
                        self.logger.debug("Skipping due to invalid scheme detected in the path " + url.geturl())
                        continue

                    # Test for obscure use case and try to patch it over.
                    if uri.netloc and not uri.scheme:
                        self.logger.debug("Handling odd case where no scheme was specified.")
                        # It should be reasonable to adopt the parent's scheme
                        uri_parts[0] = url.scheme

                    # If we have a relative url only (e.g. /foo/bar) make it
                    # an absolute so we can attempt to crawl it...
                    if not uri.scheme and not uri.netloc:
                        # A full (/foo/bar) path was specified
                        self.logger.debug("Converting relative URL " + uri.geturl() + " to absolute.")
                        uri_parts[0] = url.scheme
                        if uri.path[0] == "/" or not self.fp_match.match(url.path):
                            uri_parts[1] = url.netloc
                        else:
                            # Localized path (baz/bep), so we need the parent's path
                            uri_parts[1] = url.netloc
                            uri_parts[2] = self.fp_match.match(url.path).group(0) + uri.path

                    # Reassemble the URL after the futzing we just did...
                    uri = urlparse(urlunparse(uri_parts))

                    # Filter out and handle stupid shit like .. and . (WARNING: BIG FAT KLUDGE)
                    uri = self.resolveComponents(uri)

                    self.logger.debug("New absolute URL is " + uri.geturl())

                    if not re.search(self.search_fqdn, str(uri.hostname)) and not url:
                        self.logger.info("Crawling link <" + str(uri.geturl()) + "> for parent URL " + str(url.geturl()))

                    self.log_url(url=uri, backlink=url)

            except Exception as error:
                self.log_url(url=url, error=str(error), status_code=909)
                self.logger.error("Error trying to crawl " + glob_uri.geturl())
                self.logger.error("Crawling on behalf of URL " + url.geturl())
                self.logger.error(error)
                self.logger.error(traceback.format_exc())
                pass

    def crawl_page(self, input_url):

        url_record = self.instantiate_url(input_url)

        if not url_record.is_crawled:
            self.logger.info("Crawling " + input_url.geturl())

            session = requests.Session()
            session.headers.update(self.config.sessionconfig['headers'])
            session.max_redirects = self.config.sessionconfig['sessionopts']['max_redirects']

            urls = []
            # Check our blacklist
            is_blacklisted = False
            if input_url.hostname in self.config.blacklist:
                # If empty, the entire server is is_blacklisted
                if self.config.blacklist[input_url.hostname] == {}:
                    is_blacklisted=True
                # Check to see if the scheme is blocked
                if 'scheme' in self.config.blacklist[input_url.hostname]:
                    if input_url.scheme == self.config.blacklist[input_url.hostname]['scheme']:
                        is_blacklisted = True
                # Check to see if the path is blocked
                if 'path' in self.config.blacklist[input_url.hostname]:
                    if input_url.path == self.config.blacklist[input_url.hostname]['path']:
                        is_blacklisted = True
                # Check to see if the netloc is blocked
                if 'netloc' in self.config.blacklist[input_url.hostname]:
                    if input_url.path == self.config.blacklist[input_url.hostname]['netloc']:
                        is_blacklisted = True

            # Check for other bad situations (e.g. links with malformed mailto:, etc.)
            if [invalid_token for invalid_token in self.config.httpconfig['invalid_tokens'] if re.search(invalid_token, input_url.geturl())]:
                is_blacklisted = True

            if is_blacklisted:
                self.logger.info("Logging and disqualifying is_blacklisted URL: " + input_url.geturl())
                self.log_url(url=input_url, record=url_record, is_blacklisted=True)
                return


            content_type = None
            status_code = None
            links = None
            text = None

            try:
                with session.get(input_url.geturl(), verify=False, timeout=10, allow_redirects=True) as r:

                    # Log the status code (we assume it won't change in the next millisecond)
                    status_code = r.status_code

                    # Grab the text (if any)
                    text = r.text

                    # Determine the content type up front to determine what we do
                    # with the target later.
                    if 'Content-Type' in r.headers:
                        content_type = r.headers['Content-Type']
                        self.logger.debug("Content-type for URL: " + input_url.geturl() + " is " + content_type)

                    # Unpack any redirects we stumbled upon so we have record of those
                    if r.history:
                        self.logger.debug("Redirect(s) for URL: " + input_url.geturl())

                        previous_url = None

                        # Log all of the redirects between the specified URL and the real destination
                        for redirect in r.history:
                            if previous_url:
                                self.logger.debug("URL: " + input_url.geturl() + " redirects through " + previous_url.geturl() + " via " + redirect.url + ".")     
                            else:
                                self.logger.debug("URL: " + input_url.geturl() + " redirects through " + " via " + redirect.url + ".")     

                            self.log_url(url=urlparse(redirect.url), backlink=previous_url, redirect_parent=previous_url, pagelinks=[], is_crawled=True, status_code=redirect.status_code)
                            previous_url = urlparse(redirect.url)

                        # Log the final landing place.
                        self.logger.debug("URL: " + input_url.geturl() + " redirects through " + r.url + " via " + previous_url.geturl() + ".")
                        self.log_url(url=urlparse(r.url), pagelinks=[], backlink=previous_url, is_crawled=True, redirect_parent=previous_url, status_code=r.status_code)

                    # The web server will (should) return the "most correct" URL, let's try to use that...
                    urls.append(urlparse(r.url))
                    
                    # Handle edge case where people are linking to a URL that isn't quite proper, but 
                    # is indexed anyway.
                    if input_url.geturl() != r.url:
                        urls.append(input_url)

            except Exception as error:
                # Add the URL to the list of found urls with a 0 value
                # so that we don't keep trying...
                self.logger.error("Error trying to crawl " + input_url.geturl())
                self.logger.error(error)
                self.logger.error(traceback.format_exc())
                self.log_url(url=input_url, record=url_record, error=str(error), status_code=909)
                pass

            # We only want to crawl if there is something to crawl...
            for url in urls:
                if status_code not in range(400, 599) and content_type in self.config.httpconfig['allowed_content_types']:

                    # We only want to crawl things that haven't been is_crawled and only sites ending in our root stem
                    self.logger.debug('URL: ' + url.geturl())
                    if re.search(self.search_fqdn, url.hostname) and self.sub_path_match.match(url.path):
                        soup = BeautifulSoup(text, features="html5lib")
                        links = [urlparse(str(x.get('href'))) for x in soup.find_all('a')]

                        # Log that we're crawling the specified url
                        if self.log_url(url=url, pagelinks=[x.geturl() for x in links], content_type=content_type, status_code=status_code):
                            # Crawl the links on the given url
                            self.logger.debug("Enqueuing URL for link crawl: " + url.geturl())
                            # Push the link onto the link queue for processing
                            try:
                                link_payload = json.dumps({ 'links': [x.geturl() for x in links], 'url': url.geturl() })
                                self.mq.queue_push(self.config.mqueue['queues']['link'], link_payload)
                            except TypeError as te:
                                self.logger.error(te)
                                from pprint import pprint
                                print('-----------------------------------------------')
                                pprint([x.geturl() for x in links])
                                pprint(url)
                                print('-----------------------------------------------')
                        else:
                            self.logger.debug("Skipping crawl -- already is_crawled: " + url.geturl())

                    else:
                        # Log, but not crawl, the external links
                        self.logger.info("Logging, but not crawling, external site: " + url.geturl() + " STATUS CODE " + str(status_code))
                        self.log_url(url=url, content_type=content_type, status_code=status_code)

                else:
                    # Log everything else as some sort of other content that would not have links
                    # or is otherwise an error, and then do not attempt to crawl further.
                    self.logger.debug("Not crawling for links in URL: " + url.geturl() + " STATUS CODE " + str(status_code))
                    self.log_url(url=url, content_type=content_type, status_code=status_code)
        else:
            self.logger.info("URL '%s' already crawled. Skipping.", input_url.geturl())