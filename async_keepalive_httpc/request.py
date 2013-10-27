#!/usr/bin/env python
import collections
import cStringIO as StringIO
import socket
import urlparse
import logging
import datetime
import re

import tornado.ioloop
import tornado.iostream


class UrlInfo(object):
    def __init__(self, url):
        self.p = urlparse.urlparse(url)

    @property
    def uri(self):
        if not self.p.params:
            return self.p.path 
        else:
            return self.p.path + '?' + self.p.params

    @property
    def port(self):
        if self.p.port:
            return self.p.port

        if self.p.scheme.lower() == 'http':
            return 80

        if self.p.scheme.lower() == 'https':
            return 443

    @property
    def host(self):
        return self.p.hostname.lower()

    @property
    def is_ssl(self):
        return 's' in self.p.scheme.lower()

    @property
    def connection_key(self):
        return '{}://{}:{}'.format(self.p.scheme.lower(), self.host, self.port)


class Request(object):

    head_tpl = b'{method} {uri} HTTP/{version}'

    http_ret_pattern = re.compile('^[^\s]+ (\d+) (.+)$')

    default_headers = {
        'Accept': '*/*',
        'User-Agent': 'KeepAliveHttpClient',
        'Connection': 'Keep-Alive',
    }

    def __init__(self, url_info, method="GET", callback=None, extra_headers=[], version='1.1'):
        self.finish_cb = None
        self.url_info = url_info
        self.method = method
        assert callback != None
        self.cb = callback
        self.headers = {}
        self.extra_headers = extra_headers
        self.logger = logging.getLogger(Request.__class__.__name__)
        self.version = version

        self.resp_header = {}
        self.resp_code = None
        self.resp_text = None
        self.resp_data = None
        self.close_after_finish = False
        self.try_count = 0
        self.is_server_keep_alive = False
        self.finishes_at = None
        self.started_at = None
        self.elapsed = None
        self.stage = 'created'
        self.error = None
        self.should_disconnect = True

    @property
    def uri(self):
        return self.url_info.uri

    def reset(self):
        self.stage = 'reseted'
        self.finishes_at = None
        self.started_at = None
        self.elapsed = None
        self.last_action_at = None

    def tick_elapsed(self):
        if self.stage not in ['created', 'reseted']:
            self.elapsed = datetime.datetime.now() - self.started_at

    def set_finish_cb(self, cb):
        self.finish_cb = cb

    def header(self):
        str_buf = StringIO.StringIO()

        str_buf.write(
            self.head_tpl.format(
                method=self.method,
                uri=self.url_info.uri, 
                version=self.version
            )
        )

        str_buf.write(b'\r\n')

        headers = {}
        headers.update(self.default_headers)
        headers.update(self.extra_headers)
        headers['Host'] = self.url_info.p.netloc

        for h in ['Host', 'Accept', 'User-Agent']:
            str_buf.write(b'{}: {}'.format(h, headers.pop(h)))
            str_buf.write(b'\r\n')

        for h, v in headers.items():
            str_buf.write(b'{}: {}'.format(h, headers.pop(h)))
            str_buf.write(b'\r\n')

        str_buf.write(b'\r\n')
        ret = str_buf.getvalue()
        return ret

    def action(self, stream):
        self.started_at = datetime.datetime.now()
        self.stage = 'started'
        self.try_count += 1
        self.stream = stream
        self.stream.write(self.header())
        self.stream.read_until(
            b"\r\n\r\n", self._on_header)

    def _exception_handle(self, e):
        self.should_disconnect = True
        self.error = e
        self.logger.warn('Failed to perform: {} {}'.format(self.method, 
            self.url_info.uri))

        if self.error:
            self.logger.exception(self.error)
        try: 
            self.cb(self)
        finally:
            self._on_finish()

    def _on_header(self, data):
        if self.stage == 'reseted':
            return

        self.stage = 'on_header'
        self.last_action_at = datetime.datetime.now()
        self.resp_header = {}
        lines = data.split(b"\r\n")

        m = self.http_ret_pattern.match(lines[0])
        if m:
            self.resp_code = m.groups()[0]
            self.resp_text = m.groups()[1]

        try:
            for line in lines[1:] :
               parts = line.split(b":")
               if len(parts) == 2:
                   self.resp_header[parts[0].strip()] = parts[1].strip()

            if 'Connection' in self.resp_header:
                if self.resp_header['Connection'].lower() == 'keep-alive':
                    self.should_disconnect = False

            if 'Content-Length' in self.resp_header:
                self.stream.read_bytes(
                    int(self.resp_header[b'Content-Length']), self._on_body)
            else:
                self._exception_handle('Chunk encoding not supported')
        except Exception, e:
            self._exception_handle(e)

    def _on_body(self, data):
        if self.stage == 'reseted':
            return

        self.stage = 'on_body'
        self.last_action_at = datetime.datetime.now()
        try:
            self.resp_data = data
            self.cb(self)
        except Exception, e:
            self._exception_handle(e)
        finally:
            self._on_finish()

    def _on_finish(self):
        if self.stage == 'reseted':
            return

        self.stage = 'finished'
        self.tick_elapsed()
        '''
        Set self.stream to None and call the finish_cb
        '''
        self.stream = None
        self.finishes_at = datetime.datetime.now()
        self.finish_cb(self)

    def timeout(self):
        self.stage = 'timeout'
        self.current_request = None
        self._exception_handle('Timeout')


class IdleTimer(object):
    def __init__(self):
        now = datetime.datetime.now()
        self.idle_start = now
        self.last_idle = now

    def tick(self):
        self.last_idle = datetime.datetime.now()

    def reset(self):
        now = datetime.datetime.now()
        self.idle_start = now
        self.last_idle = now

    @property
    def idle_elapsed(self):
        return self.last_idle - self.idle_start


class QueueManager(object):


    def __init__(self, io_loop, host, port, is_ssl, 
            request_timeout=datetime.timedelta(seconds=30),
            idle_timout=datetime.timedelta(seconds=30),
            check_feq = datetime.timedelta(seconds=1)
        ):

        self.logger = logging.getLogger(QueueManager.__class__.__name__)

        self._q = collections.deque([])

        self.host = host
        self.port = port
        self.io_loop = io_loop

        self.is_ssl = is_ssl
        self.stream = None

        self.current_request = None
        self.last_request = None
        self.connect_count = 0

        self.idle_timer = IdleTimer()

        self.request_timeout = request_timeout
        self.idle_timout = idle_timout

        self.check_scheduler = tornado.ioloop.PeriodicCallback(
            self.check,
            check_feq.total_seconds() * 1000,
            io_loop=self.io_loop
        )

        self.check_scheduler.start()

    def _update_request(self):
        self.logger.info("_update_request: %s" % self.current_request.url_info.uri)
        if self.current_request:
            self.last_request = self.current_request
            self.current_request = None

            if self.last_request.should_disconnect:
                self.disconnect()

    @property
    def waiting_len(self):
        return len(self._q)

    def close(self):
        self.logger.info("close")
        self.check_scheduler.stop()

        try:
            self.stream.close()
        except Exception, e:
            self.logger.exception(e)

        self.stream = None

    def connect(self):
        self.logger.info('connecting to {}:{}'.format(self.host, self.port))
        self.connect_count += 1
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)

        self.stream = tornado.iostream.IOStream(s, 
            io_loop=self.io_loop)
        self.logger.info("stream created: %s" % self.stream)
        self.stream.connect(
            (self.host, int(self.port)),
            self.process_request)

        self.stream.set_close_callback(self._on_stream_close)

    def disconnect(self):
        self.idle_timer.reset()
        self.logger.info('disconnecting...')
        try:
            if self.stream:
                self.stream.close()
        except Exception, e:
            self.logger.exception(e)
        finally:
            self.stream = None

    def check(self, *args, **kwargs):
        self.logger.info("check")
        if self.current_request:
            self.current_request.tick_elapsed()

            if self.current_request.elapsed >= self.request_timeout:
                self.current_request.timeout()

        if len(self._q):
            self.process_request()
        else:
            self.idle_timer.tick()

            if self.idle_timer.idle_elapsed >= self.idle_timout:
                self.logger.info('idle timeout')
                self.disconnect()


    def process_request(self):
        self.logger.info("process_request")
        if self.stream is None and len(self._q):
            self.logger.info("1")
            self.connect()
            return

        if self.stream.closed() and len(self._q):
            self.logger.info("2")
            self.connect()
            return

        if self.current_request:
            self.logger.info("3")
            return

        if len(self._q):
            self.logger.info("4")
            self.current_request = self._q.popleft()
            self.current_request.action(self.stream)
            self.idle_timer.reset()
            return

        self.logger.info("5")


    def _on_request_finished(self, request):
        assert(request == self.current_request)
        self._update_request()
        self.process_request()
    
    def add(self, request):
        '''
        Set self.stream to None and call the finish_cb
        '''
        request.set_finish_cb(
            self._on_request_finished)
        self._q.append(request)

    def _on_stream_close(self):
        # try:
        #     if self.stream:
        #         self.stream.close()
        # except Exception, e:
        #     self.logger.exception(e)
        # finally:
        #self.stream = None
        pass

