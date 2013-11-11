import logging
import urllib
import md5
import functools

import xmltodict

from async_keepalive_httpc.keepalive_client import SimpleKeepAliveHTTPClient
from async_keepalive_httpc.aws.auth import EasyV4Sign

sqs_v_logger = logging.getLogger("sqs_verification")


def md5_hexdigest(data):
    m = md5.new()
    m.update(data)
    return m.hexdigest()


def verify_send(response, expact_md5=None, callback=None):
    sqs_v_logger.info("resp [%s - %s]: \n" % 
        (response.code, response.reason))

    if response.code != 200:
        sqs_v_logger.warn("resp [%s - %s]: \n %s" % (
            response.code, response.reason, response.body))
    else:
        sqs_result = xmltodict.parse(response.body)
        msg_id = sqs_result['SendMessageResponse']['SendMessageResult']['MessageId']
        msg_md5 = sqs_result['SendMessageResponse']['SendMessageResult']['MD5OfMessageBody']

        if expact_md5 != msg_md5:
            sqs_v_logger.warn("md5 is not matched. Expect: {}, Received: {}".format(expact_md5, msg_md5))
        else:
            sqs_v_logger.info("msg send sucessfully with id: %s" % msg_id)

    if callback:
        callback(response)


class SQSQueue(object):
    _version = "2012-11-05"

    def __init__(self, io_loop,
        access_key, secret_key, q_url, 
        endpoint='ap-southeast-2'):
        self.access_key = access_key
        self.secret_key = secret_key
        self.q_url = q_url
        self.endpoint = endpoint
        self.v4sign = EasyV4Sign(
            self.access_key, self.secret_key,
            'sqs',
            endpoint=self.endpoint
        )
        self.logger = logging.getLogger(SQSQueue.__name__)
        self.io_loop = io_loop
        self.client = SimpleKeepAliveHTTPClient(self.io_loop)


    def send(self, msg, callback=None, headers={}):

        msg_body = urllib.quote_plus(msg)

        data = {
            'Action': 'SendMessage', 
            'MessageBody': msg_body,
            'Version': '2012-11-05',
        }

        x_method, x_url, x_headers, x_body = self.v4sign.sign_post(
            self.q_url, headers, data=data)
        md5_unquoted= md5_hexdigest(msg)
        self.logger.debug('authinfo  for {} is {}'.format(msg_body, x_headers['Authorization']))

        cb = functools.partial(verify_send, expact_md5=md5_unquoted, callback=callback)
        return self.client.fetch(x_url, callback=cb, method='POST', headers=x_headers, body=x_body)

    def get(self, message_number=1):
        pass

