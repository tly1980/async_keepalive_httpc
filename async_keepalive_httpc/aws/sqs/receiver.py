import logging
import datetime
import functools


import tornado
import xmltodict

from async_keepalive_httpc.request import UrlInfo, Request, QueueManager

from async_keepalive_httpc.aws.auth import EasyV4Sign

sqs_recv_logger = logging.getLogger("sqs_recv")


def extract_msg(request, callback=None):
    messages = None

    if request.resp_code != 200:
        sqs_recv_logger.warn("resp body: \n%s" % request.resp_data)
        sqs_recv_logger.warn("orig req: \n%s" % request.req())
    else:
        messages = xmltodict.parse(request.resp_data)

    if callback:
        callback(request, messages)


class Receiver(object):
    _version = "2012-11-05"

    def __init__(self, 
        access_key, secret_key, q_url, 
        endpoint='ap-southeast-2',
        max_wait_sec=10,
        max_number_of_msg=10,
        request_timeout=datetime.timedelta(seconds=30),
        idle_timout=datetime.timedelta(seconds=30),
        check_feq=datetime.timedelta(seconds=1),
        max_connection=4, io_loop=tornado.ioloop.IOLoop.instance()):
        self.q_url_info = UrlInfo(q_url)
        self.q_url = q_url
        self.sq_mgr = QueueManager(
            io_loop,
            self.q_url_info.host,
            self.q_url_info.port,
            self.q_url_info.is_ssl,
        )
        self.logger = logging.getLogger(Receiver.__class__.__name__)
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint
        self.v4sign = EasyV4Sign(
            self.access_key, self.secret_key,
            'sqs',
            endpoint=self.endpoint
        )
        self.max_wait_sec = max_wait_sec
        self.max_number_of_msg = max_number_of_msg


    def receive(self, callback=None):

        params = {
            'Action': 'ReceiveMessage', 
            'WaitTimeSeconds': self.max_wait_sec,
            'MaxNumberOfMessages': self.max_number_of_msg,
            'Version': self._version
        }

        x_method, x_url, x_headers, x_body = self.v4sign.sign_get(
            self.q_url, self._header_tpl, params=params)

        cb = functools.partial(extract_msg, callback=callback)


        r = Request(UrlInfo(x_url), method="GET", 
                callback=cb, extra_headers=x_headers, body=x_body)
        self.sq_mgr.add(r)
