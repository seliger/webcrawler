#!/usr/bin/env python3

import shelve
import csv

data_file = 'crawler-data-ALL.csv'

rd = {}


def resolve_redirect(url, count=0):
    count += 1
    if url in rd and count < 10:
        url = resolve_redirect(rd[url], count)
    return url


#with shelve.open('crawler-cache.db', 'r') as raw_data:
with shelve.open('temp.db', 'r') as raw_data:

    print("Loading all URLs...")
    data = dict(raw_data)

    rd = { data[z]['redirect_parent']:z for z in [x for x in data.keys() if data[x]['redirect_parent']] }

    print("Filtering URLs")

    # Loads all entries
    urls = [x for x in data.keys()]
    #  Loads all of the 4xx entries
    #urls = [x for x in data.keys() if data[x]['status_code'] in range(400, 499)]

    print("Total URLs loaded: " + str(len(urls)))

    counter = 0
    with open(data_file, 'w') as out:
        csvout = csv.writer(out, delimiter='\t', quotechar='"', lineterminator="\n", quoting=csv.QUOTE_ALL)

        csvout.writerow(["Target", "Root Stem", "Content-Type", "Status Code", "Source"])
        for url in urls:
            counter += 1
            for backlink in data[url]['backlinks']:
                csvout.writerow([resolve_redirect(url), data[url]['root_stem'], data[url]['content_type'], data[url]['status_code'], backlink])
            if counter % 100 == 0:
                print("URLs processed thus far: " + str(counter))
