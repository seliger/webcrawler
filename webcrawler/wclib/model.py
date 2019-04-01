from peewee import *
from playhouse.shortcuts import model_to_dict, dict_to_model


database_proxy = Proxy()

class DataModelConfig:
    def __init__(self, config):
        database_proxy.initialize(MySQLDatabase(config.dbname, **config.dbconfig))

class UnknownField(object):
    def __init__(self, *_, **__): pass

class BaseModel(Model):
    class Meta:
        database = database_proxy

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

class URL(BaseModel):
    scan_id = ForeignKeyField(column_name='scan_id', field='scan_id', model=Scan)
    url_id = CharField()
    url_text = TextField(null=True)
    root_stem = TextField(null=True)
    fqdn = TextField(null=True)
    found_timestamp = DateTimeField(null=True)

    class Meta:
        table_name = 'URLs'
        indexes = (
            (('url_id', 'scan_id'), True),
        )
        primary_key = CompositeKey('scan_id', 'url_id')

class ScannedURL(BaseModel):
    scan_id = ForeignKeyField(column_name='scan_id', field='scan_id', model=URL)
    url_id = ForeignKeyField(backref='URLs_url_set', column_name='url_id', field='url_id', model=URL)
    is_crawled = IntegerField(null=True)
    is_blacklisted = IntegerField(null=True)
    redirect_parent_scan = ForeignKeyField(column_name='redirect_parent_scan_id', field='scan_id', model='self', null=True)
    redirect_parent_url = ForeignKeyField(backref='ScannedURLs_redirect_parent_url_set', column_name='redirect_parent_url_id', field='url_id', model='self', null=True)
    scan_timestamp = DateTimeField(null=True)
    status_code = CharField(null=True)
    content_type = CharField(null=True)
    page_title = TextField(null=True)

    class Meta:
        table_name = 'ScannedURLs'
        indexes = (
            (('redirect_parent_scan', 'redirect_parent_url'), False),
            (('scan_id', 'url_id'), True),
        )
        primary_key = CompositeKey('scan_id', 'url_id')

class Backlink(BaseModel):
    scan_id = ForeignKeyField(backref='ScannedURLs_scan_set', column_name='scan_id', field='scan_id', model=ScannedURL)
    url_id = ForeignKeyField(backref='ScannedURLs_url_set', column_name='url_id', field='url_id', model=ScannedURL)
    backlink_scan = ForeignKeyField(column_name='backlink_scan_id', field='scan_id', model=ScannedURL, null=True)
    backlink_url = ForeignKeyField(backref='ScannedURLs_backlink_url_set', column_name='backlink_url_id', field='url_id', model=ScannedURL, null=True)

    class Meta:
        table_name = 'Backlinks'
        indexes = (
            (('backlink_scan', 'backlink_url'), False),
            (('scan_id', 'url_id'), True),
        )
        primary_key = CompositeKey('scan_id', 'url_id')

class PageLink(BaseModel):
    scan_id = ForeignKeyField(column_name='scan_id', field='scan_id', model=ScannedURL)
    url_id = ForeignKeyField(backref='ScannedURLs_url_set', column_name='url_id', field='url_id', model=ScannedURL)
    link = TextField(null=True)
    linktext = TextField(null=True)

    class Meta:
        table_name = 'PageLinks'
        indexes = (
            (('scan_id', 'url_id'), True),
        )
        primary_key = CompositeKey('scan_id', 'url_id')

class ScanBlacklist(BaseModel):
    scan_id = ForeignKeyField(column_name='scan_id', field='scan_id', model=Scan)
    fqdn = CharField()
    path = TextField(null=True)

    class Meta:
        table_name = 'ScanBlackLists'
        indexes = (
            (('scan_id', 'fqdn', 'path'), True),
        )
        primary_key = False


class ScanError(BaseModel):
    scan_id = ForeignKeyField(column_name='scan_id', field='scan_id', model=ScannedURL)
    url_id = ForeignKeyField(backref='ScannedURLs_url_set', column_name='url_id', field='url_id', model=ScannedURL)
    error_text = TextField(null=True)

    class Meta:
        table_name = 'ScanErrors'
        indexes = (
            (('scan_id', 'url_id'), True),
        )
        primary_key = CompositeKey('scan_id', 'url_id')

class ScanRoot(BaseModel):
    scan = ForeignKeyField(column_name='scan_id', field='scan_id', model=Scan)
    fqdn = CharField()
    port = CharField(null=True)

    class Meta:
        table_name = 'ScanRoots'
        indexes = (
            (('scan_id', 'fqdn', 'port'), True),
        )
        primary_key = False
