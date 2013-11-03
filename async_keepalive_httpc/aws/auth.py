import tornado.httpclient
import tornado.gen
import botocore.credentials
from botocore.auth import SigV4Auth
import datetime


class DummyRequest(object):
    '''
    A FakeRequest that provide all the necessary properties and interface for botocore to authenticate
    '''

    def __init__(
        self, method, url, headers={}, params={}, body=None):
        self.url = url
        self.headers = dict(headers)
        self.method = method
        self.params = dict(params)
        self.body=body


def sqs_request(msg):
    query = {
        'Action': 'SendMessage', 
        'MessageBody': msg,
        'Version': '2012-11-05',
        'Connection': 'Keep-Alive'
    }

    l = ['='.join([k, query[k]]) for k in sorted(query.keys())]
    body = '&'.join(l)
    
    
    frequset = DummyRequest(
        'POST',
        SQS_ENDPOINT,
        headers={
            'Content-type': 'application/x-www-form-urlencoded; charset=utf-8'
        },
        body=body
    )

    credentials = botocore.credentials.Credentials(
            ACCESS_KEY, SECRET_KEY)

    s = SigV4Auth(credentials, 'sqs', 'ap-southeast-2')
    s.add_auth(frequset)
    return tornado.httpclient.HTTPRequest(
        frequset.url,
        method=frequset.method,
        headers=frequset.headers,
        body=frequset.body
    )


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


    def sign(self, 
              url, 
          headers, 
             body,
             method='POST', timestamp=None):

        r = DummyRequest(method, url, headers=headers, body=body)

        s = SigV4Auth(
            self.credentials, self.service, self.endpoint)
        if timestamp:
            s.timestamp = timestamp
        else:
            s.timestamp = datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        s.add_auth(r)
        
        return (r.method, r.url, r.headers, r.body)

