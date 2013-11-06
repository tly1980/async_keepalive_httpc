import logging
import urllib
import md5
import functools


import tornado
import xmltodict


from async_keepalive_httpc.pool import KeepAlivePool
from async_keepalive_httpc.request import UrlInfo, Request

from async_keepalive_httpc.aws.auth import EasyV4Sign

sqs_v_logger = logging.getLogger("sqs_verification")


def md5_hexdigest(data):
    m = md5.new()
    m.update(data)
    return m.hexdigest()


def verify_and_callback(request, expact_md5=None, callback=None):
    sqs_v_logger.debug("resp code / text: %s - %s" %(request.resp_code, request.resp_text))
    if request.resp_code != 200:
        sqs_v_logger.warn("resp body: \n%s" % request.resp_data)
        sqs_v_logger.warn("orig req: \n%s" % request.req())
        
    else:
        sqs_result = xmltodict.parse(request.resp_data)
        msg_id = sqs_result['SendMessageResponse']['SendMessageResult']['MessageId']
        msg_md5 = sqs_result['SendMessageResponse']['SendMessageResult']['MD5OfMessageBody']
        if expact_md5 != msg_md5:
            sqs_v_logger.warn("md5 is not matched. Expect: {}, Received: {}".format(expact_md5, msg_md5))
        else:
            sqs_v_logger.info("msg send sucessfully with id: %s" % msg_id)

    if callback:
        callback(request)


class Sender(object):
    _version = "2012-11-05"

    def __init__(self, 
        access_key, secret_key, q_url, 
        endpoint='ap-southeast-2',
        max_connection=4, io_loop=tornado.ioloop.IOLoop.instance()):
        self.q_url_info = UrlInfo(q_url)
        self.q_url = q_url
        self.ka_httpc_pool = KeepAlivePool(
            self.q_url_info.host,
            port=self.q_url_info.port,
            is_ssl=self.q_url_info.is_ssl,
            init_count=1,
            max_count=max_connection,
            io_loop=io_loop)
        self.logger = logging.getLogger(Sender.__class__.__name__)
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self.v4sign = EasyV4Sign(
            self.access_key, self.secret_key,
            'sqs',
            endpoint=self.endpoint
        )


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

        sq_mgr = self.ka_httpc_pool.get()

        cb = functools.partial(verify_and_callback, expact_md5=md5_unquoted, callback=callback)

        self.logger.info('authinfo  for {} is {}'.format(msg_body,x_headers['Authorization'] ))

        r = Request(UrlInfo(x_url), method="POST", callback=cb, extra_headers=x_headers, body=x_body)
        sq_mgr.add(r)
