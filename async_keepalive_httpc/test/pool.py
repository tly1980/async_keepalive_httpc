import datetime

from tornado.testing import AsyncTestCase, gen_test
from tornado import gen
import tornado.httpserver

from async_keepalive_httpc.request import Request, UrlInfo
from async_keepalive_httpc.pool import KeepAlivePool


class PoolTest(AsyncTestCase):

    port = 18181

    def setUp(self):
        #super(PoolTest, self).setUp()
        AsyncTestCase.setUp(self)

        self.ka_httpc_pool = KeepAlivePool(
            'localhost',
            port=self.port,
            is_ssl=False,
            init_count=1,
            max_count=3,
            io_loop=self.io_loop)

        self.create_server()

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


    def get(self, sq_mgr, url, callback=None):
        url_info = UrlInfo(url)
        if not callback:
            callback = lambda r: r
        r = Request(url_info, method="GET", callback=callback)
        sq_mgr.add(r)


    @gen_test
    def test_pool(self):
        sq_mgr1 = self.ka_httpc_pool.get()
        self.get(sq_mgr1, 'http://localhost:{}/a.txt'.format(self.port))

        sq_mgr2 = self.ka_httpc_pool.get()
        self.get(sq_mgr2, 'http://localhost:{}/a.txt'.format(self.port))

        self.assertEqual(
            len(self.ka_httpc_pool._pool), 2)

        sq_mgr3 = self.ka_httpc_pool.get()
        self.get(sq_mgr3, 'http://localhost:{}/a.txt'.format(self.port))

        self.assertEqual(
            len(self.ka_httpc_pool._pool), 3)

        self.assertNotEqual(sq_mgr2, sq_mgr1)
        self.assertNotEqual(sq_mgr2, sq_mgr3)
        self.assertNotEqual(sq_mgr1, sq_mgr3)

        sq_mgr4 = self.ka_httpc_pool.get()
        self.get(sq_mgr4, 'http://localhost:{}/a.txt'.format(self.port))

        self.assertEqual(sq_mgr1, sq_mgr4)

        sq_mgr5 = self.ka_httpc_pool.get()
        self.assertEqual(sq_mgr2, sq_mgr5)






