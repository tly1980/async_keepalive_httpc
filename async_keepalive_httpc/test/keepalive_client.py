import datetime
import unittest
import os

import tornado.httpserver
from tornado.testing import AsyncTestCase, gen_test
#from tornado.httpclient import AsyncHTTPClient
from tornado import gen
from async_keepalive_httpc.keepalive_client import SimpleKeepAliveHTTPClient


if os.environ.get('PROXY_HOST'):

    PROXY_CONFIG = dict(
        zip(
            ['proxy_host', 'proxy_port'],
            [os.environ.get('PROXY_HOST'), int(os.environ.get('PROXY_PORT'))]
        )
    )

else:
    PROXY_CONFIG = {}

class SimpleKeepAliveHTTPClientTestCase(AsyncTestCase):
    '''
    This would be treated as a simple template
    '''
    port = 18181

    def create_server(self):
        @gen.coroutine
        def handle_request(request):
            message = "You requested %s\n" % request.uri
            if request.uri == '/timeout':
                print "timeout hitted"
                yield gen.Task(
                    self.io_loop.add_timeout, datetime.timedelta(seconds=3))
                print "timeout continue"


            request.write("HTTP/1.1 200 OK\r\nContent-Length: %d\r\nConnection: Keep-Alive\r\n\r\n%s" % (len(message), message))
            request.finish()

        self.http_server = tornado.httpserver.HTTPServer(handle_request, io_loop=self.io_loop)
        self.http_server.listen(self.port)

    @gen_test(timeout=10)
    def test_keep_alive_get(self):
        self.create_server()
        ska_client = SimpleKeepAliveHTTPClient(self.io_loop)

        a = yield ska_client.fetch('http://localhost:{}/a.txt'.format(self.port))
        b = yield ska_client.fetch('http://localhost:{}/b.txt'.format(self.port))
        c = yield ska_client.fetch('http://localhost:{}/c.txt'.format(self.port))

        self.assertIn('a.txt', a.body)
        self.assertIn('b.txt', b.body)
        self.assertIn('c.txt', c.body)
        self.assertEqual(ska_client.connection.connect_times, 1)

    @gen_test
    def test_keep_alive_get_2(self):
        self.create_server()
        ska_client = SimpleKeepAliveHTTPClient(self.io_loop)

        self.assertEqual(0, len(ska_client))

        ska_client.fetch('http://localhost:{}/a.txt'.format(self.port))
        ska_client.fetch('http://localhost:{}/b.txt'.format(self.port))
        ska_client.fetch('http://localhost:{}/c.txt'.format(self.port))

        self.assertEqual(2, len(ska_client.queue))
        self.assertEqual(3, len(ska_client))

        d = yield ska_client.fetch('http://localhost:{}/c.txt'.format(self.port))

        self.assertIn('c.txt', d.body)

        self.assertIsNone(ska_client.connection.final_callback)

        self.assertEqual(ska_client.connection.connect_times, 1)


    @gen_test(timeout=10)
    def test_idle_timeout(self):
        self.create_server()
        ska_client = SimpleKeepAliveHTTPClient(self.io_loop, idle_timeout=0.1)

        a = yield ska_client.fetch('http://localhost:{}/a.txt'.format(self.port))
        self.assertIn('a.txt', a.body)
        self.assertEqual(ska_client.connection.connect_times, 1)

        self.assertEqual(ska_client.connection.stream.closed(), False)

        yield gen.Task(
                    self.io_loop.add_timeout, datetime.timedelta(seconds=0.11))

        b = yield ska_client.fetch('http://localhost:{}/b.txt'.format(self.port))

        self.assertIn('b.txt', b.body)

        yield gen.Task(
                    self.io_loop.add_timeout, datetime.timedelta(seconds=0.08))

        c = yield ska_client.fetch('http://localhost:{}/c.txt'.format(self.port))

        self.assertIn('c.txt', c.body)

        self.assertEqual(ska_client.connection.connect_times, 2)

        yield gen.Task(
            self.io_loop.add_timeout, datetime.timedelta(seconds=0.11))
        
        self.assertEqual(ska_client.connection.stream.closed(), True)

    @unittest.skipIf(not PROXY_CONFIG, "HTTP_PROXY enviornment variable is not set.")
    @gen_test(timeout=10)
    def test_proxy(self):
        self.create_server()
        ska_client = SimpleKeepAliveHTTPClient(self.io_loop, idle_timeout=0.1)

        c = yield ska_client.fetch('http://localhost:{}/c.txt'.format(self.port),
            proxy_host='localhost', proxy_port=8888)

        self.assertIn('c.txt', c.body)

        # g = yield ska_client.fetch('http://www.google.com/'.format(self.port),
        #     proxy_host='localhost', proxy_port=8888)

        #self.assertIn('c.txt', c.body)

        self.assertEqual(ska_client.connection.stream.closed(), True)

