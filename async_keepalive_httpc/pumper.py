#!/usr/bin/env python
import collections
import cStringIO as StringIO
import logging
import datetime
import pprint

import tornado.ioloop
import tornado.iostream

from .utils import SmartUrl, Request, StreamQueueManager

class HttpKeepAliveClient(object):

    def __init__(self, io_loop=tornado.ioloop.IOLoop.instance()):
        self.sq_pool = {}
        self.logger = logging.getLogger(
            HttpKeepAliveClient.__class__.__name__)
        self.io_loop = io_loop

    def get(self, url, cb=None):
        if not cb:
            cb = self.on_resp

        smart_url = SmartUrl(url)
        if smart_url.connection_key not in self.sq_pool:
            self.sq_pool[smart_url.connection_key] = StreamQueueManager(
                smart_url.host, smart_url.port, smart_url.is_ssl)

        sq_manager = self.sq_pool[smart_url.connection_key]
        sq_manager.add(Request(smart_url, method='GET', cb=cb))

    def on_resp(self, request):
        if self.logger.isEnabledFor(logging.INFO):
            buf = StringIO.StringIO()
            pp = pprint.PrettyPrinter(stream=buf)
            pp.pprint("{} - {}".format(request.resp_code, request.resp_text))
            pp.pprint(request.resp_header)
            pp.pprint(
                "{}...<total {} bytes>".format(
                    request.resp_data[:10], len(request.resp_data)
                    )
            )
            self.logger.info(buf.getvalue())
            buf.close()

    def check(self):
        for key, sq_manager in self.sq_pool.items():
            sq_manager.process_request()

        self.io_loop.add_timeout(datetime.timedelta(seconds=1), self.check)


ka_client = HttpKeepAliveClient()
ka_client.get("http://localhost:9000/ab.txt")
ka_client.get("http://localhost:9000/ba.txt")

tornado.ioloop.IOLoop.instance().add_callback(ka_client.check)

tornado.ioloop.IOLoop.instance().start()

