import botocore.credentials
from botocore.auth import SigV4Auth
import datetime


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


class EasyV4Sign(object):

    def __init__(self, 
            access_key, secret_key,
            service,
            endpoint='ap-southeast-2'):

        self.endpoint = endpoint
        self.access_key = access_key
        self.secret_key = secret_key
        self.credentials = botocore.credentials.Credentials(
            self.access_key, self.secret_key)
        self.service = service
        self.sigV4auth = SigV4Auth(
            self.credentials, self.service, self.endpoint)


    def sign_post(self, url, headers, data={}, timestamp=None):
        new_headers = dict(headers)

        l = ['='.join([k, data[k]]) for k in sorted(data.keys())]
        body = '&'.join(l)
        new_headers['Content-type'] = 'application/x-www-form-urlencoded; charset=utf-8'

        r = DummyRequest('POST', url, headers=new_headers, body=body)

        if timestamp:
            self.sigV4auth.timestamp = timestamp
        else:
            self.sigV4auth.timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        self.sigV4auth.add_auth(r)

        return (r.method, r.url, r.headers, r.body)

    def sign_get(self, url, headers, params={}, timestamp=None):
        new_headers = dict(headers)

        r = DummyRequest('GET', url, headers=new_headers)

        if timestamp:
            self.sigV4auth.timestamp = timestamp
        else:
            self.sigV4auth.timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')

        self.sigV4auth.add_auth(r)

        return (r.method, r.url, r.headers, r.body)

