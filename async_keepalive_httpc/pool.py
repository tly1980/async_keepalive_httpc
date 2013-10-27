#!/usr/bin/env python
import cStringIO as StringIO
import logging
import datetime
import pprint

import tornado.ioloop
import tornado.iostream

from .utils import UrlInfo, Request, StreamQueueManager


class KeepAlivePool(object):

    def __init__(self, host, port=80, is_ssl=False, 
                    init_count=0, max_count=4,
                    io_loop=tornado.ioloop.IOLoop.instance()):
        self.host = host
        self.port = port
        self.is_ssl = is_ssl
        self._pool = []
        self.init_count = init_count
        self.max_count = max_count
        self.logger = logging.getLogger(
            KeepAlivePool.__class__.__name__)
        self.io_loop = io_loop

    def get(self):
        fast_sq_mgr = min(self._pool, key=lambda s:s.waiting_len)
        if len(fast_sq_mgr.waiting_len) == 0 or len(self._pool) == self.max_count:
            return fast_sq_mgr

        sq_mgr = StreamQueueManager(self.host, self.port, self.is_ssl)
        self._pool.append(sq_mgr)

        return sq_mgr
