import datetime
import unittest

import tornado.httpserver
from tornado.testing import AsyncTestCase, gen_test
#from tornado.httpclient import AsyncHTTPClient
from tornado import gen


from async_keepalive_httpc.request import QueueManager, Request, UrlInfo


# class SimpleTestCase(AsyncTestCase):
#     '''
#     This would be treated as a simple template
#     '''
#     port = 8888

#     def create_server(self):
#         def handle_request(request):
#             message = "You requested %s\n" % request.uri
#             request.write("HTTP/1.1 200 OK\r\nContent-Length: %d\r\n\r\n%s" % (len(message), message))
#             request.finish()

#         self.http_server = tornado.httpserver.HTTPServer(handle_request, io_loop=self.io_loop)
#         self.http_server.listen(self.port)

#     def test_http_fetch(self):
#         self.create_server()
#         client = AsyncHTTPClient(self.io_loop)
#         client.fetch('http://localhost:{}/a.txt'.format(self.port), self.handle_fetch)
#         self.wait()

#     def handle_fetch(self, response):
#         self.assertIn("a.txt", response.body)
#         self.stop()


class UrlInfoTest(unittest.TestCase):
    def test_http(self):
        urlinfo = UrlInfo('http://LOCALHOST/abc?a=23&b=456')
        self.assertEqual(urlinfo.host, 'localhost')
        self.assertEqual(urlinfo.port, 80)
        self.assertEqual(urlinfo.is_ssl, False)
        self.assertEqual(urlinfo.uri_with_query, '/abc?a=23&b=456')

    def test_https(self):
        urlinfo = UrlInfo('https://localhost/abc')
        self.assertEqual(urlinfo.port, 443)
        self.assertEqual(urlinfo.is_ssl, True)
        self.assertEqual(urlinfo.is_ssl, True)


class QueueManagerTestCase(AsyncTestCase):
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

    @gen_test
    def test_keep_alive_get(self):
        self.create_server()
        self.sq_mgr = QueueManager(self.io_loop, 
            'localhost', self.port, False)

        a, b, c = yield [
          gen.Task(self.get, 'http://localhost:{}/a.txt'.format(self.port)),
          gen.Task(self.get, 'http://localhost:{}/b.txt'.format(self.port)),
          gen.Task(self.get, 'http://localhost:{}/c.txt'.format(self.port))
        ]

        self.assertEqual(0, len(self.sq_mgr._q))
        self.assertIn('a.txt', a.resp_data)
        self.assertIn('b.txt', b.resp_data)
        self.assertIn('c.txt', c.resp_data)
        self.assertEqual(self.sq_mgr.connect_count, 1)

    def get(self, url, callback=None):
        url_info = UrlInfo(url)
        r = Request(url_info, method="GET", callback=callback)
        self.sq_mgr.add(r)

    @gen_test(timeout=10)
    def test_request_timeout(self):
        self.create_server()
        self.sq_mgr = QueueManager(self.io_loop, 
            'localhost', self.port, False,
            request_timeout=datetime.timedelta(seconds=2.5))


        tout = yield gen.Task(
          self.get, 
          'http://localhost:{}/timeout'.format(self.port))

        self.assertIn('Timeout', tout.error)
        self.assertIn('timeout', tout.stage)

        a = yield gen.Task(self.get, 'http://localhost:{}/a.txt'.format(self.port))
        self.assertEqual(self.sq_mgr.connect_count, 2)
        self.assertIn('a.txt', a.resp_data)


    @gen_test(timeout=5)
    def test_idle_timout(self):
        '''
        The sq_mgr should disconnect automatically after being idle
        for a specific time
        '''

        self.create_server()
        self.sq_mgr = QueueManager(self.io_loop, 
            'localhost', self.port, False,
            idle_timout=datetime.timedelta(seconds=1),
            check_feq = datetime.timedelta(seconds=0.1))

        a, b, c = yield [
          gen.Task(self.get, 'http://localhost:{}/a.txt'.format(self.port)),
          gen.Task(self.get, 'http://localhost:{}/b.txt'.format(self.port)),
          gen.Task(self.get, 'http://localhost:{}/c.txt'.format(self.port))
        ]

        self.assertIn('a.txt', a.resp_data)
        self.assertIn('b.txt', b.resp_data)
        self.assertIn('c.txt', c.resp_data)

        self.assertIsNotNone(self.sq_mgr.stream)
        self.assertFalse(self.sq_mgr.stream.closed())

        # 
        yield gen.Task(self.io_loop.add_callback)

        self.assertEqual(
            self.sq_mgr.current_request, None)

        self.assertEqual(self.sq_mgr.connect_count, 1)

        self.assertEqual(self.sq_mgr.stream.closed(),
            False)

        # let the event loop to have cpu controll here, 
        # so they it can do the disconnect

        yield gen.Task(
            self.io_loop.add_timeout,
            datetime.timedelta(seconds=1.5))

        self.assertEqual(self.sq_mgr.stream, None)
        #self.fail('just to check the log')

    @gen_test()
    def test_update_request(self):
        self.create_server()
        self.sq_mgr = QueueManager(self.io_loop, 
            'localhost', self.port, False,
            idle_timout=datetime.timedelta(seconds=1),
            check_feq = datetime.timedelta(seconds=0.1))

        yield gen.Task(self.get, 'http://localhost:{}/a.txt'.format(self.port))

        self.assertEqual(
            self.sq_mgr.last_request,  None)

        self.assertEqual(
            self.sq_mgr.current_request.uri, '/a.txt')

        yield gen.Task(self.get, 'http://localhost:{}/b.txt'.format(self.port))

        self.assertEqual(
            self.sq_mgr.last_request.uri, '/a.txt')

        self.assertEqual(
            self.sq_mgr.current_request.uri, '/b.txt')

        #self.fail('just to check the log')
