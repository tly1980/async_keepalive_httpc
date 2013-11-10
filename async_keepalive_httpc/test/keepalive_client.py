import datetime

import tornado.httpserver
from tornado.testing import AsyncTestCase, gen_test
#from tornado.httpclient import AsyncHTTPClient
from tornado import gen
from async_keepalive_httpc.keepalive_client import SimpleKeepAliveHTTPClient



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

        ska_client.fetch('http://localhost:{}/a.txt'.format(self.port))
        ska_client.fetch('http://localhost:{}/b.txt'.format(self.port))
        ska_client.fetch('http://localhost:{}/c.txt'.format(self.port))

        self.assertEqual(2, len(ska_client.queue))

        d = yield ska_client.fetch('http://localhost:{}/c.txt'.format(self.port))

        self.assertIn('c.txt', d.body)

        self.assertEqual(ska_client.connection.connect_times, 1)


    @gen_test(timeout=10)
    def test_request_timeout(self):
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


    # @gen_test(timeout=5)
    # def test_idle_timout(self):
    #     '''
    #     The sq_mgr should disconnect automatically after being idle
    #     for a specific time
    #     '''

    #     self.create_server()
    #     self.sq_mgr = QueueManager(self.io_loop, 
    #         'localhost', self.port, False,
    #         idle_timout=datetime.timedelta(seconds=1),
    #         check_feq = datetime.timedelta(seconds=0.1))

    #     a, b, c = yield [
    #       gen.Task(self.get, 'http://localhost:{}/a.txt'.format(self.port)),
    #       gen.Task(self.get, 'http://localhost:{}/b.txt'.format(self.port)),
    #       gen.Task(self.get, 'http://localhost:{}/c.txt'.format(self.port))
    #     ]

    #     self.assertIn('a.txt', a.resp_data)
    #     self.assertIn('b.txt', b.resp_data)
    #     self.assertIn('c.txt', c.resp_data)

    #     self.assertIsNotNone(self.sq_mgr.stream)
    #     self.assertFalse(self.sq_mgr.stream.closed())

    #     # 
    #     yield gen.Task(self.io_loop.add_callback)

    #     self.assertEqual(
    #         self.sq_mgr.current_request, None)

    #     self.assertEqual(self.sq_mgr.connect_count, 1)

    #     self.assertEqual(self.sq_mgr.stream.closed(),
    #         False)

    #     # let the event loop to have cpu controll here, 
    #     # so they it can do the disconnect

    #     yield gen.Task(
    #         self.io_loop.add_timeout,
    #         datetime.timedelta(seconds=1.5))

    #     self.assertEqual(self.sq_mgr.stream, None)
    #     #self.fail('just to check the log')

    # @gen_test()
    # def test_update_request(self):
    #     self.create_server()
    #     self.sq_mgr = QueueManager(self.io_loop, 
    #         'localhost', self.port, False,
    #         idle_timout=datetime.timedelta(seconds=1),
    #         check_feq = datetime.timedelta(seconds=0.1))

    #     yield gen.Task(self.get, 'http://localhost:{}/a.txt'.format(self.port))

    #     self.assertEqual(
    #         self.sq_mgr.last_request,  None)

    #     self.assertEqual(
    #         self.sq_mgr.current_request.uri, '/a.txt')

    #     yield gen.Task(self.get, 'http://localhost:{}/b.txt'.format(self.port))

    #     self.assertEqual(
    #         self.sq_mgr.last_request.uri, '/a.txt')

    #     self.assertEqual(
    #         self.sq_mgr.current_request.uri, '/b.txt')

        #self.fail('just to check the log')
