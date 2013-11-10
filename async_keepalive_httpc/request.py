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
        return self.p.path 

    @property
    def uri_with_query(self):
        if self.p.query:
            return self.p.path + '?' + self.p.query
        else:
            return self.p.path


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
        'User-Agent': 'AsyncKeepAliveHttpC',
        'Connection': 'Keep-Alive',
    }

    def __init__(self, url_info, method="GET", body=None, callback=None, extra_headers=[], version='1.1'):
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
        self.body = body

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

    def req(self):
        str_buf = StringIO.StringIO()

        str_buf.write(
            self.head_tpl.format(
                method=self.method,
                uri=self.url_info.uri_with_query, 
                version=self.version
            )
        )

        str_buf.write(b'\r\n')

        headers = {}
        headers.update(self.default_headers)
        headers.update(self.extra_headers)
        headers['Host'] = self.url_info.p.netloc

        if self.body:
            headers['Content-Length'] = len(self.body)

        for h in ['Host', 'Accept', 'User-Agent']:
            if h in headers:
                str_buf.write(b'{}: {}'.format(h, headers.pop(h)))
                str_buf.write(b'\r\n')

        for h, v in headers.items():
            str_buf.write(b'{}: {}'.format(h, headers.pop(h)))
            str_buf.write(b'\r\n')

        str_buf.write(b'\r\n')

        if self.body:
            str_buf.write(self.body)

        ret = str_buf.getvalue()
        return ret

    def action(self, stream):
        self.started_at = datetime.datetime.now()
        self.stage = 'started'
        self.try_count += 1
        self.stream = stream
        req = self.req()

        self.stream.write(req)
        self.logger.debug(req)

        self.stream.read_until(
            b"\r\n\r\n", self._on_header)

    def _exception_handle(self, e):
        self.should_disconnect = True
        self.error = e
        self.logger.warn('Failed to perform: {} {}'.format(self.method, 
            self.url_info.uri))
        if self.error:
            self.logger.exception(self.error)

        if self.cb:
            self.cb(self)

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
            self.resp_code = int(m.groups()[0])
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

        if self.stage != 'timeout':
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
        self._exception_handle('Timeout')


