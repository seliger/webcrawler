#!/usr/bin/env python3

import requests
import re
import urllib3
import json
import time
import datetime
import logging
import shelve
import posixpath
import traceback

from bs4 import BeautifulSoup
from urllib.parse import urlparse, urlunparse
from requests.packages.urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter


# Fugly workaround to stop SSL errors (not checking for valid certs...)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Kludgy config
seed_site = 'https://www.purdue.edu/'
search_fqdn = 'purdue\.edu$'
invalid_tokens = ['http[s]?://mailto:']
root_fqdns = ['purdue.edu', 'purdue.edu:80', 'purdue.edu:443', 
              'www.purdue.edu', 'www.purdue.edu:80', 'www.purdue.edu:443']
schemes = ['http', 'https']
invalid_schemes = ['tel:', 'mailto:']

blacklist = {
                'wpvappwt01.itap.purdue.edu' : {},
                'www.purdue.edu' : {'path': '/diversity-inclusion/events'},
                'extension.purdue.edu' : {'path': '/events'},
                'lslab.ics.purdue.edu': {'path': '/icsWeb/LabSchedules'},
                'web.ics.purdue.edu': { 'path': '/~apo/SheetSigns.php'}
            }

path_match = re.compile('^/([^/]+)/?')
fp_match = re.compile('^(.*[/])')

# Allowed Content-types:
allowed_content_types = ['text/html', 'text/html; charset=UTF-8', 'text/html; charset=utf-8']

# Set up logging
loglevel = logging.INFO
logger = logging.getLogger('webcrawler')
logger.setLevel(loglevel)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

fh = logging.FileHandler('webcrawler.log')
fh.setLevel(loglevel)
fh.setFormatter(formatter)

ch = logging.StreamHandler()
ch.setLevel(loglevel)
ch.setFormatter(formatter)

logger.addHandler(ch)
logger.addHandler(fh)

# Ugly but necessary (for now)
global found_urls
global found_fqdns
global counter
global log_op_counter
global total_counter

found_fqdns = {}
counter = 0
total_counter = 0
crawler_cycle_counter = 0
log_op_counter = 0

session = requests.Session()
session.max_redirects = 10

headers = {}
headers['Upgrade-Insecure-Requests'] = "1"
headers['User-Agent'] = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.92 Safari/537.36'
headers['DNT'] = "1"
headers['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8'
headers['Accept-Encoding'] = 'gzip, deflate, br'
headers['Accept-Language'] = 'en-US,en;q=0.9'
headers['Range'] = 'bytes=0-1000000'
session.headers.update(headers)

# retries = Retry(total=3,
#                 read=3,
#                 connect=3,
#                 redirect=5,
#                 backoff_factor=0.1,
#                 status_forcelist=(500, 502, 503, 504))
# session.mount('http://', HTTPAdapter(max_retries=retries))
# session.mount('https://', HTTPAdapter(max_retries=retries))


def resolveComponents(url):
    orig_url = url
    if url.path:
        url = url._replace(path=posixpath.normpath(url.path))

    logger.debug("resolveComponents(): OLD PATH: " + orig_url.path + " NEW PATH: " + url.path)
    return url


def make_url(url_text=None):
    found_urls[url_text] = {
        "crawled": False,
        "blacklisted": False,
        "pagelinks": [],
        "backlinks": {},
        "redirect_parent": None,
        "status_code": None,
        "root_stem": None,
        "content_type": None
    }


def log_url(url=None, backlink=None, pagelinks=None, content_type=None, status_code=None, error=None, blacklisted=False, redirect_parent=None, crawled=False):
    global found_urls
    global found_fqdns
    global counter
    global total_counter
    global log_op_counter

    found_url = None

    # Establish if we even have a record for this url; if not add one.
    if url.geturl() not in found_urls:
        logger.debug("log_url(): URL " + url.geturl() + " was not found; creating new record")
        make_url(url.geturl())

        # We are counting discovered pages
        counter += 1
        total_counter += 1

        # # Take actions based on counter changes
        # if counter > 0 and counter % 5000 == 0:
        #     dump_files()

    # In order to use shelve without requiring writeback, we need to create a local instance
    # of the item we are about to manipulate, manipulate it, and put it back. 
    found_url = found_urls[url.geturl()]

    # For grouping purposes, add the FQDN (or a fqdn/something)
    if not found_url['root_stem'] and url.hostname in root_fqdns and path_match.match(url.path):
        found_url['root_stem'] = url.hostname + path_match.match(url.path).group(0)
    else:
        found_url['root_stem'] = url.hostname

    # If this is a redirect, log its parent so we can retrace later
    if redirect_parent:
        found_url['redirect_parent'] = redirect_parent.geturl()

    # If backlink is None, that means we are logging an actual page crawl.
    if backlink is None:
        logger.debug("log_url(): Logging that " + url.geturl() + " has been crawled.")
        # Set the status
        found_url['crawled'] = True

        if pagelinks and not found_url['pagelinks']:
            found_url['pagelinks'] = pagelinks

        # Attach the HTTP status code and content type for the crawled web page.
        found_url['status_code'] = status_code
        found_url['content_type'] = content_type
        found_url['blacklisted'] = blacklisted

    # If backlink contains a value, that means we are writing a backlink to a different URL.
    # If it doesn't exist, we need to create it so we can populate the backlink.
    else:

        if backlink.geturl() not in found_url['backlinks']:
            logger.debug("log_url(): URL " + url.geturl() +" was found, but backlink " + backlink.geturl() + " was not found; adding.")
            found_url['backlinks'][backlink.geturl()] = 1
        else:
            logger.debug("log_url(): URL " + url.geturl() +" was found and backlink " + backlink.geturl() + " was found; incrementing.")
            found_url['backlinks'][backlink.geturl()] += 1

        if crawled:
            found_url['crawled'] = True

    # Attempt to capture the error and force the page crawled.
    if error:
        found_url['crawled'] = True
        found_url['error'] = error

    # Write the instance back to the shelve
    found_urls[url.geturl()] = found_url


    # Increment our log_op_counter and flush if we've crossed a threshold
    log_op_counter += 1
    if log_op_counter > 0 and log_op_counter % 3000 == 0:
        logger.info('log_url(): Flushing data structure to disk cache.')
        found_urls.sync()

        # Display some metrics
        logger.info("log_url(): Logged " + str(counter) + " URLs in cycle " + str(crawler_cycle_counter) + "...")
        logger.info("log_url(): " + str(total_counter) + " total pages logged across all cycles.")
        logger.info("log_url(): " + str(log_op_counter) + " log operations counted across all cycles.")

    if log_op_counter > 0 and log_op_counter % 25000 == 0:
        logger.info("log_url(): Reorganizing (shrinking) the underlying DBM file!")
        found_urls.sync()
        found_urls.dict.reorganize()
        found_urls.sync()
        logger.info("log_url(): Reorganizing complete!")

        # Display some more metrics
        logger.info("log_url(): " + str(total_counter) + " total pages logged across all cycles.")
        current_keys = found_urls.keys()
        not_crawled = len([x for x in current_keys if not found_urls[x]['crawled']])
        logger.info("log_url(): " + str(not_crawled) + " uncrawled sites identified.")

    return found_url['crawled']


def dump_files():
    logger.info("dump_files(): Dumping JSON data files...")
    found_urls.sync()

    found_urls_dict = dict(found_urls)

    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y%m%d%H%M%S')

    with open('output/urlmap_' + st + '.json', 'w') as urlmap:
        json.dump(found_urls_dict, urlmap)

    with open('output/fqdnlist_' + st + '.json', 'w') as fqdnlist:
        json.dump(found_fqdns, fqdnlist)

    # Free the memory (hopefully)
    found_urls_dict = None

    # This time to drop the memory back down
    found_urls.sync()


def crawl_links(links=None, url=None):
    # Scrape all of the links in the document and try to crawl them
    glob_uri = None
    for uri in links:
        glob_uri = uri
        try:
            logger.debug("crawl_links(): Crawling link <" + str(uri.geturl()) + "> for parent URL " + str(url.geturl()))

            if uri.netloc or (not uri.netloc and uri.path):
                logger.debug("crawl_links(): " + uri.geturl() + " has a netloc and matches search_fqdn OR no netloc and a path.")

                # 0 - scheme
                # 1 - netloc
                # 2 - path
                # 3 - params
                # 4 - query
                # 5 - fragment (#)
                uri_parts = list(uri)

                # If we have a scheme, make sure it's one we care about
                if uri.scheme and uri.scheme not in schemes:
                    logger.debug("crawl_links(): Not a valid scheme, skipping: " + uri.geturl())
                    continue

                # If we have a scheme embedded at the start of the path, something is wrong.
                if (not uri.scheme and uri.path) and any([re.search("^" + x, uri.path) for x in invalid_schemes]):
                    logger.debug("crawl_links(): Skipping due to invalid scheme detected in the path " + url.geturl())
                    continue

                # Test for obscure use case and try to patch it over.
                if uri.netloc and not uri.scheme:
                    logger.debug("crawl_links(): Handling odd case where no scheme was specified.")
                    # It should be reasonable to adopt the parent's scheme
                    uri_parts[0] = url.scheme

                # If we have a relative url only (e.g. /foo/bar) make it
                # an absolute so we can attempt to crawl it...
                if not uri.scheme and not uri.netloc:
                    # A full (/foo/bar) path was specified
                    logger.debug("crawl_links(): Converting relative URL " + uri.geturl() + " to absolute.")
                    uri_parts[0] = url.scheme
                    if uri.path[0] == "/" or not fp_match.match(url.path):
                        uri_parts[1] = url.netloc
                    else:
                        # Localized path (baz/bep), so we need the parent's path
                        uri_parts[1] = url.netloc
                        uri_parts[2] = fp_match.match(url.path).group(0) + uri.path

                # Reassemble the URL after the futzing we just did...
                uri = urlparse(urlunparse(uri_parts))

                # Filter out and handle stupid shit like .. and . (WARNING: BIG FAT KLUDGE)
                uri = resolveComponents(uri)

                logger.debug("crawl_links(): New absolute URL is " + uri.geturl())

                if not re.search(search_fqdn, str(uri.hostname)) and not url:
                    logger.info("crawl_links(): Crawling link <" + str(uri.geturl()) + "> for parent URL " + str(url.geturl()))

                # # It doesn't fix the issue, but will help gather some more context for them
                # # And given some of the horrific URLs I've found, this may be okay...
                # if not uri.hostname or not re.search(search_fqdn, uri.hostname):
                #     logger.error("crawl_links(): BIZ - Bizarre URL not being logged: " + uri.geturl())
                #     logger.error("crawl_links(): BIZ - Original URL was: " + glob_uri.geturl())
                #     logger.error("crawl_links(): BIZ - Parent URL was: " + url.geturl())
                #     continue

                # Keep a log of new FQDNs found on our search and count now many times
                # they are referenced
                if uri.hostname not in found_fqdns:
                    found_fqdns[uri.hostname] = 1
                    logger.info("crawl_links(): Discovered new FQDN: " + uri.hostname + " (" + uri.geturl() + " in " + url.geturl() +") ")
                else:
                    found_fqdns[uri.hostname] += 1

                if found_fqdns[uri.hostname] % 1000 == 0:
                    logger.info("crawl_links(): FQDN references for " + uri.hostname + ": " + str(found_fqdns[uri.hostname]))

                log_url(url=uri, backlink=url)

        except Exception as error:
            log_url(url, error=str(error), status_code=909)
            logger.error("crawl_links(): Error trying to crawl " + glob_uri.geturl())
            logger.error("crawl_links(): Crawling on behalf of URL " + url.geturl())
            logger.error(error)
            logger.error(traceback.format_exc())
            pass


def crawl_page(url):
    global found_urls
    global found_fqdns

    logger.debug("crawl_page(): Crawling " + url.geturl())

    # Check our blacklist
    blacklisted = False
    if url.hostname in blacklist:
        # If empty, the entire server is blacklisted
        if blacklist[url.hostname] == {}:
            blacklisted=True
        # Check to see if the scheme is blocked
        if 'scheme' in blacklist[url.hostname]:
            if url.scheme == blacklist[url.hostname]['scheme']:
                blacklisted = True
        # Check to see if the path is blocked
        if 'path' in blacklist[url.hostname]:
            if url.path == blacklist[url.hostname]['path']:
                blacklisted = True
        # Check to see if the netloc is blocked
        if 'netloc' in blacklist[url.hostname]:
            if url.path == blacklist[url.hostname]['netloc']:
                blacklisted = True

    # Check for other bad situations (e.g. links with malformed mailto:, etc.)
    if [invalid_token for invalid_token in invalid_tokens if re.search(invalid_token, url.geturl())]:
        blacklisted = True

    if blacklisted:
        logger.info("crawl_page(): Logging and disqualifying blacklisted URL: " + url.geturl())
        log_url(url=url, blacklisted=True)
        return


    content_type = None
    status_code = None
    links = None
    text = None

    try:
        with session.get(url.geturl(), verify=False, timeout=10, allow_redirects=True) as r:

            # Log the status code (we assume it won't change in the next millisecond)
            status_code = r.status_code

            # Grab the text (if any)
            text = r.text

            # Determine the content type up front to determine what we do
            # with the target later.
            if 'Content-Type' in r.headers:
                content_type = r.headers['Content-Type']
                logger.debug("crawl_page(): Content-type for URL: " + url.geturl() + " is " + content_type)

            # Unpack any redirects we stumbled upon so we have record of those
            if r.history:
                logger.debug("crawl_page(): Redirect(s) for URL: " + url.geturl())

                previous_url = None

                # Log all of the redirects between the specified URL and the real destination
                for redirect in r.history:
                    if previous_url:
                        logger.debug("crawl_page(): URL: " + url.geturl() + " redirects through " + previous_url.geturl() + " via " + redirect.url + ".")     
                    else:
                        logger.debug("crawl_page(): URL: " + url.geturl() + " redirects through " + " via " + redirect.url + ".")     

                    log_url(url=urlparse(redirect.url), backlink=previous_url, redirect_parent=previous_url, pagelinks=[], crawled=True, status_code=redirect.status_code)
                    previous_url = urlparse(redirect.url)

                # Log the final landing place.
                logger.debug("crawl_page(): URL: " + url.geturl() + " redirects through " + r.url + " via " + previous_url.geturl() + ".")
                log_url(url=urlparse(r.url), pagelinks=[], backlink=previous_url, crawled=True, redirect_parent=previous_url, status_code=r.status_code)

            # The web server will (should) return the "most correct" URL, let's try to use that...
            url = urlparse(r.url)

    except Exception as error:
        # Add the URL to the list of found urls with a 0 value
        # so that we don't keep trying...
        log_url(url, error=str(error), status_code=909)
        logger.error("crawl_page(): Error trying to crawl " + url.geturl())
        logger.error(error)
        logger.error(traceback.format_exc())
        pass

    # We only want to crawl if there is something to crawl...
    if status_code not in range(400, 599) and content_type in allowed_content_types:

        # We only want to crawl things that haven't been crawled and only sites ending in our root stem
        if re.search(search_fqdn, url.hostname):
            soup = BeautifulSoup(text, features="html5lib")
            links = [urlparse(x.get('href')) for x in soup.find_all('a')]

            # Log that we're crawling the specified url
            if log_url(url=url, pagelinks=[x.geturl() for x in links], content_type=content_type, status_code=status_code):
                # Crawl the links on the given url
                logger.debug("crawl_page(): Invoking crawl_links for URL: " + url.geturl())
                crawl_links(links, url)
            else:
                logger.debug("crawl_page(): Skipping crawl -- already crawled: " + url.geturl())

        else:
            # Log, but not crawl, the external links
            logger.info("crawl_page(): Logging, but not crawling, external site: " + url.geturl() + " STATUS CODE " + str(status_code))
            log_url(url=url, content_type=content_type, status_code=status_code)

    else:
        # Log everything else as some sort of other content that would not have links
        # or is otherwise an error, and then do not attempt to crawl further.
        logger.debug("crawl_page(): Not crawling for links in URL: " + url.geturl() + " STATUS CODE " + str(status_code))
        log_url(url=url, content_type=content_type, status_code=status_code)



# Main execution loop
with shelve.open('fqdn-cache.db', 'c', writeback=False) as found_fqdns:
    with shelve.open('crawler-cache.db', 'c', writeback=False) as found_urls:
        # Seed the first site into the dict
        if len(found_urls) == 0:
            make_url(seed_site)
        else:
            total_counter = len(found_urls)

        while True:
            uncrawled_urls = [urlparse(x) for x in found_urls.keys() if not found_urls[x]['crawled']]

            if len(uncrawled_urls) == 0:
                break

            crawler_cycle_counter += 1
            counter = 0
            logger.info("main(): Crawler Cycle " + str(crawler_cycle_counter))
            logger.info("main():     " + str(len(uncrawled_urls)) + " uncrawled in this crawler cycle.")

            for uncrawled_url in uncrawled_urls:
                crawl_page(uncrawled_url)

        # logger.info("main(): Final file dump...")
        # dump_files()
        logger.info("main(): Total logged pages: " + str(total_counter))
