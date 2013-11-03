#!/usr/bin/env python
import logging

import tornado.ioloop
import tornado.iostream

from .request import QueueManager


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

    def _increase(self):
        if len(self._pool) < self.max_count:
            sq_mgr = QueueManager(
                self.io_loop, 
                self.host, self.port, self.is_ssl,
                name='queue_mgr-%s' % len(self._pool))

            self._pool.append(sq_mgr)

            return sq_mgr

    def get(self):
        if not self._pool:
            return self._increase()

        fast_sq_mgr = min(self._pool, key=lambda s:s.waiting_len)

        if fast_sq_mgr.waiting_len == 0:
            return fast_sq_mgr

        if len(self._pool) < self.max_count:
            return self._increase()

        return fast_sq_mgr

