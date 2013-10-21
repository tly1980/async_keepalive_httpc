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


class SmartUrl(object):
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
        "Accept": "*/*", 
        "User-Agent": "KeepAliveHttpClient"
    }

    def __init__(self, the_url, method="GET", cb=None, exception_cb=None, extra_headers=[]):
        self.finish_cb = None
        self.the_url = the_url
        self.method = method
        self.cb = cb
        self.exception_cb = exception_cb
        self.headers = {}
        self.extra_headers = extra_headers
        self.logger = logging.getLogger(Request.__class__.__name__)

        self.resp_header = {}
        self.resp_code = None
        self.resp_text = None
        self.resp_data = None

        self.try_count = 0

    def set_finish_cb(self, cb):
        self.finish_cb = cb

    def header(self, version='1.1'):
        str_buf = StringIO.StringIO()

        str_buf.write(
            self.head_tpl.format(
                method=self.method,
                uri=self.the_url.uri, 
                version=version
            )
        )

        str_buf.write(b'\r\n')

        headers = {}
        headers.update(self.default_headers)
        headers.update(self.extra_headers)
        headers['Host'] = self.the_url.p.netloc

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
        self.try_count += 1
        self.stream = stream
        self.stream.write(self.header())
        self.stream.read_until(
            b"\r\n\r\n", self._on_header)

    def _exception_cb(self, headers, e):
        self.logger.warn('Failed to perform: {} {}', self.method, self.the_url.uri)
        if e:
            self.logger.exception(e)

    def _on_header(self, data):
        import ipdb; ipdb.set_trace()
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
                   self.headers[parts[0].strip()] = parts[1].strip()

            if b'Content-Length' in self.headers:
                self.stream.read_bytes(
                    int(self.headers[b'Content-Length']), self._on_body)
            else:
                self.exception_cb(self, None)
        except Exception, e:
            self.exception_cb(self, e)
            self._on_finish()

    def _on_body(self, data):
        try:
            self.resp_data = data
            self.cb(self)
        except Exception, e:
            self.exception_cb(self.headers, e)
        finally:
            self._on_finish()

    def _on_finish(self):
        '''
        Set self.stream to None and call the finish_cb
        '''
        self.stream = None
        self.finish_cb(self)


class StreamQueueManager(object):
    def __init__(self, host, port, is_ssl):
        self._q = collections.deque([])

        self.host = host
        self.port = port

        self.is_ssl = is_ssl
        self.stream = None
        self.idle_duration = 0
        self.last_idle = datetime.datetime.now()

        self.current_request = None

    def connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)
        self.stream = tornado.iostream.IOStream(s)
        self.stream.connect(
            (self.host, int(self.port)),
            self.process_request)
        self.stream.set_close_callback(self._on_stream_close)

    def process_request(self):
        if not self.stream:
            self.connect()
            return

        if self.current_request:
            return

        if len(self._q):
            self.current_request = self._q.popleft()
            self.current_request.action(self.stream)
            self.idle_duration = datetime.timedelta()
        else:
            now = datetime.datetime.now()
            self.idle_duration = now - self.last_idle
            self.last_idle = now
            print "idle", self.idle_duration


    def _on_request_finished(self, request):
        assert(request == self.current_request)
        self.current_request = None
        self.process_request()
    
    def add(self, request):
        '''
        Set self.stream to None and call the finish_cb
        '''
        request.set_finish_cb(
            self._on_request_finished)
        self._q.append(request)

    def _on_stream_close(self):
        self.current_request = None
        if len(self._q) > 0:
            self.connect()

