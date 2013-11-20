import logging

import botocore.credentials
from botocore.auth import SigV4Auth
import datetime
import dateutil.parser
from dateutil.tz import tzutc

from async_keepalive_httpc.utils import json


class DummyRequest(object):
    '''
    A DummyRequest that provide all the necessary properties and interface for botocore to authenticate
    Important: it would create a new dict to copy the headers, so that it would not messed with the original dict.
    '''

    def __init__(
        self, method, url, headers={}, params={}, body=None):
        self.url = url
        self.headers = headers
        self.method = method
        self.params = params
        self.body = body

        if params:
            l = ['='.join([k, str(params[k])]) for k in sorted(params.keys())]
            qry_string = '&'.join(l)

            self.url = '{}?{}'.format(self.url, qry_string)


class EasyV4Sign(object):

    def __init__(self, 
            access_key, secret_key,
            service,
            region='ap-southeast-2'):

        self.region = region
        self.access_key = access_key
        self.secret_key = secret_key
        self.credentials = botocore.credentials.Credentials(
            self.access_key, self.secret_key)
        self.service = service
        self.sigV4auth = SigV4Auth(
            self.credentials, self.service, self.region)


    def sign_post(self, url, headers, data={}, timestamp=None):
        new_headers = dict(headers)

        l = ['='.join([k, str(data[k])]) for k in sorted(data.keys())]
        body = '&'.join(l)
        if 'Content-Type' not in new_headers:
            new_headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=utf-8'

        r = DummyRequest('POST', url, headers=new_headers, body=body, params={})

        if timestamp:
            self.sigV4auth.timestamp = timestamp
        else:
            self.sigV4auth.timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        self.sigV4auth.add_auth(r)

        return (r.method, r.url, r.headers, r.body)

    def sign_json(self, url, headers, data={}, timestamp=None):
        new_headers = dict(headers)

        body = json.dumps(data)
        if 'Content-Type' not in new_headers:
            new_headers['Content-Type'] = 'application/x-amz-json-1.0'

        r = DummyRequest('POST', url, headers=new_headers, body=body, params={})

        if timestamp:
            self.sigV4auth.timestamp = timestamp
        else:
            self.sigV4auth.timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        self.sigV4auth.add_auth(r)

        return (r.method, r.url, r.headers, r.body)


    def sign_get(self, url, headers, params={}, timestamp=None):
        new_headers = dict(headers)

        r = DummyRequest('GET', url, headers=new_headers, params=params)

        if timestamp:
            self.sigV4auth.timestamp = timestamp
        else:
            self.sigV4auth.timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        self.sigV4auth.add_auth(r)

        return (r.method, r.url, r.headers, r.body)


class IamRoleV4Sign(EasyV4Sign):
    def __init__(self, io_loop, 
        service, 
        region='ap-southeast-2',
        role = None,
        before=datetime.timedelta(minutes=5)):
        self.io_loop = io_loop
        self.service = service
        self.region = region
        self.before = before
        self.role = role
        self.logger = logging.getLogger(self.__class__.__name__)
        self.start()

    def start(self):
        self.logger.info('about to get new credentials')
        self.credentials = botocore.credentials.search_iam_role()
        self.sigV4auth = SigV4Auth(
            self.credentials, self.service, self.region)

        self.logger.info('finish getting new credentials')

        if self.role:
            role_metadata = botocore.credentials._search_md()[self.role]
        else:
            role_metadata = botocore.credentials._search_md().values()[0]

        utc_expiration = dateutil.parser.parse(role_metadata['Expiration'])
        
        t_delta = utc_expiration - datetime.datetime.now(tzutc()) - self.before
        self.logger.info('next time to get credentials would be {} seconds later'.format(
            t_delta.total_seconds()))
        self._timeout = self.io_loop.add_timeout(t_delta, self.start)

