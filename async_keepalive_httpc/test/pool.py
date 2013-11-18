import datetime

from tornado.testing import AsyncTestCase, gen_test
from async_keepalive_httpc.keepalive_client import SimpleKeepAliveHTTPClient
from async_keepalive_httpc.pool import ResourcePool


class ResourcePoolTestCase(AsyncTestCase):

    @gen_test
    def test_basic(self):
        create_func = lambda: SimpleKeepAliveHTTPClient(self.io_loop)
        pool = ResourcePool(create_func, init_count=2, max_count=3)

        self.assertEqual(len(pool._pool), 2)
        ska_client1 = pool.get()
        ska_client1.fetch('http://www.google.com')
        ska_client2 = pool.get()

        self.assertNotEqual(ska_client1, ska_client2)

        ska_client2.fetch('http://www.google.com')

        ska_client3 = pool.get()

        ska_client3.fetch('http://www.google.com')

        self.assertNotEqual(ska_client1, ska_client3)
        self.assertNotEqual(ska_client2, ska_client3)

        ska_client2.fetch('http://www.google.com')
        ska_client3.fetch('http://www.google.com')

        ska_client4 = pool.get()
        self.assertEqual(ska_client1, ska_client4)

