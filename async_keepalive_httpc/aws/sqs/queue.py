import logging
import urllib
import md5
import functools

import xmltodict
import shortuuid

import tornado.httpclient

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


def verify_send_batch(response,  request=None, expact_md5s=None, callback=None):
    assert(request==response.request)
    sqs_v_logger.info("resp [%s - %s]: \n" % 
        (response.code, response.reason))
    if response.code != 200:
        sqs_v_logger.warn("resp [%s - %s]: \n %s" % (
            response.code, response.reason, response.body))
    else:
        sqs_result = xmltodict.parse(response.body)
        for r in sqs_result['SendMessageBatchResponse']['SendMessageBatchResult']['SendMessageBatchResultEntry']:
            msg_id = r['Id']
            msg_md5 = r['MD5OfMessageBody']
            expact_md5 = expact_md5s.get(msg_id, None)

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
        endpoint='ap-southeast-2', verify=True):
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
        self.verify = verify


    def send(self, msg, callback=None, headers={}):
        msg_body = urllib.quote_plus(msg)

        data = {
            'Action': 'SendMessage', 
            'MessageBody': msg_body,
            'Version': '2012-11-05',
        }

        x_method, x_url, x_headers, x_body = self.v4sign.sign_post(
            self.q_url, headers, data=data)
        if self.verify:
            md5_unquoted= md5_hexdigest(msg)
            self.logger.debug('authinfo  for {} is {}'.format(msg_body, x_headers['Authorization']))

            cb = functools.partial(verify_send, expact_md5=md5_unquoted, callback=callback)
        else:
            cb = callback
        return self.client.fetch(x_url, callback=cb, method='POST', headers=x_headers, body=x_body)

    def send_batch(self, messages=[], callback=None, headers={}):

        data = {
            'Action': 'SendMessageBatch', 
            'Version': '2012-11-05',
        }

        x_method, x_url, x_headers, x_body = self.v4sign.sign_post(
            self.q_url, headers, data=data)

        r = tornado.httpclient.HTTPRequest(x_url, method='POST', headers=x_headers, body=x_body)


        if self.verify:
            expact_md5s = {}

            for i, m in enumerate(messages, 1):
                n_id = 'SendMessageBatchRequestEntry.{}.Id'.format(i)
                n_body = 'SendMessageBatchRequestEntry.{}.MessageBody'.format(i)
                m_body = urllib.quote_plus(m)

                data[n_id] = shortuuid.uuid()
                data[n_body] = m_body
                expact_md5s[data[n_id]] = md5_hexdigest(m)

            cb = functools.partial(verify_send_batch, request=r, expact_md5s=expact_md5s, callback=callback)
        else:
            cb = callback

        self.logger.debug('send_batch authinfo is {}'.format(x_headers['Authorization']))

        return self.client.fetch(r, callback=cb, method='POST')


    def get(self, message_number=1):
        pass

    def __len__(self):
        return len(self.client)

