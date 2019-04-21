from peewee import *
from playhouse.shortcuts import model_to_dict, dict_to_model


database = Proxy()

def init(config):
    database.initialize(MySQLDatabase(config.dbname, **config.dbconfig))

# Kludge... Get rid of...
def init2(dbname, dbconfig):
    database.initialize(MySQLDatabase(dbname, **dbconfig))


class UnknownField(object):
    def __init__(self, *_, **__): pass

class BaseModel(Model):
    class Meta:
        database = database

class Scan(BaseModel):
    scan_id = AutoField()
    name = CharField(unique=True)
    description = TextField(null=True)
    start_timestamp = DateTimeField(null=True)
    end_timestamp = DateTimeField(null=True)
    seed_url = TextField(null=True)
    search_fqdn_re = TextField(null=True)
    sub_path_re = TextField(null=True)

    class Meta:
        table_name = 'Scans'

class FoundURL(BaseModel):
    url_id = AutoField()
    scan_id = ForeignKeyField(column_name='scan_id', field='scan_id', model=Scan)
    url_hash = CharField(null=True)
    url_text = TextField(null=True)
    root_stem = TextField(null=True)
    fqdn = TextField(null=True)
    is_crawled = IntegerField(null=True)
    is_blacklisted = IntegerField(null=True)
    next_url_id = ForeignKeyField(column_name='next_url_id', field='url_id', model='self', null=True)
    status_code = CharField(null=True)
    content_type = CharField(null=True)
    page_title = TextField(null=True)
    created_timestamp = DateTimeField(null=True)
    crawled_timestamp = DateTimeField(null=True)

    class Meta:
        table_name = 'FoundURLs'
        indexes = (
            (('scan', 'root_stem'), False),
            (('scan', 'url_hash'), False),
            (('scan', 'url_hash'), True),
        )

class Backlink(BaseModel):
    url_id = ForeignKeyField(backref='FoundURLs_url_set', column_name='url_id', field='url_id', model=FoundURL)
    backlink_url_id = ForeignKeyField(column_name='backlink_url_id', field='url_id', model=FoundURL)
    backlink_timestamp = DateTimeField(null=True)

    class Meta:
        table_name = 'Backlinks'
        primary_key = False

class PageLink(BaseModel):
    url_id = ForeignKeyField(column_name='url_id', field='url_id', model=FoundURL)
    link = TextField()
    linktext = TextField(null=True)

    class Meta:
        table_name = 'PageLinks'
        primary_key = False

class ScanBlacklist(BaseModel):
    scan_id = ForeignKeyField(column_name='scan_id', field='scan_id', model=Scan)
    fqdn = CharField()
    path = CharField(null=True)
    scheme = CharField(null=True)
    netloc = CharField(null=True)
    query = CharField(null=True)

    class Meta:
        table_name = 'ScanBlackLists'
        primary_key = False


class ScanError(BaseModel):
    url_id = ForeignKeyField(column_name='url_id', field='url_id', model=FoundURL)
    error_text = TextField(null=True)
    error_timestamp = DateTimeField(null=True)

    class Meta:
        table_name = 'ScanErrors'
        primary_key = False

class ScanRoot(BaseModel):
    scan_id = ForeignKeyField(column_name='scan_id', field='scan_id', model=Scan)
    fqdn = CharField()
    port = CharField(null=True)

    class Meta:
        table_name = 'ScanRoots'
        indexes = (
            (('scan_id', 'fqdn', 'port'), True),
        )
        primary_key = False
