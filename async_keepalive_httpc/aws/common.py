import logging

from tornado.curl_httpclient import CurlAsyncHTTPClient

from async_keepalive_httpc.aws.auth import EasyV4Sign
from async_keepalive_httpc.keepalive_client import SimpleKeepAliveHTTPClient

class AWSClient(object):

    def __init__(self, io_loop, access_key=None, secret_key=None, region=None, signer=None, proxy_config={}, use_curl=True):
        self.io_loop = io_loop
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.proxy_config = proxy_config

        #logger = logging.getLogger('awsclient')
        service = self._service.lower()

        if not signer :
            assert None not in (access_key, secret_key, region)
            self.v4sign = EasyV4Sign(
                self.access_key, self.secret_key,
                service,
                region=self.region
            )
        else:
            self.v4sign = signer
            signer.service = service

        # if self.proxy_config or use_curl:
        #     #print 'using proxy_config %s' % self.proxy_config
        #     if self.proxy_config:
        #         logger.debug('using proxy_config %s' % self.proxy_config)
        #     self.client = CurlAsyncHTTPClient(self.io_loop)
        #     self.use_curl = True
        # else:
        self.client = SimpleKeepAliveHTTPClient(self.io_loop)
        self.use_curl = False

    def __len__(self):
        if not self.use_curl:
            return len(self.client)
        else:
            return len(self.client._requests)

    def fire(self, r, **kwargs):
        if self.proxy_config:
            for k, v in self.proxy_config.items():
                setattr(r, k, v)

        return self.client.fetch(r, **kwargs)
