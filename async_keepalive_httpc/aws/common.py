from async_keepalive_httpc.aws.auth import EasyV4Sign
from async_keepalive_httpc.keepalive_client import SimpleKeepAliveHTTPClient


class AWSClient(object):

    def __init__(self, io_loop, access_key, secret_key, endpoint):
        self.io_loop = io_loop
        self.access_key = access_key
        self.secret_key = secret_key
        self.endpoint = endpoint

        self.v4sign = EasyV4Sign(
            self.access_key, self.secret_key,
            self._service.lower(),
            endpoint=self.endpoint
        )

        self.client = SimpleKeepAliveHTTPClient(self.io_loop)

    def __len__(self):
        return len(self.client)
