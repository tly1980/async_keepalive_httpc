from async_keepalive_httpc.aws.auth import EasyV4Sign
from async_keepalive_httpc.keepalive_client import SimpleKeepAliveHTTPClient


class AWSClient(object):

    def __init__(self, io_loop, access_key=None, secret_key=None, region=None, signer=None):
        self.io_loop = io_loop
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region

        if not signer :
            assert None not in (access_key, secret_key, region)
            self.v4sign = EasyV4Sign(
                self.access_key, self.secret_key,
                self._service.lower(),
                region=self.region
            )
        else:
            self.v4sign = signer
            signer.service = self._service

        self.client = SimpleKeepAliveHTTPClient(self.io_loop)

    def __len__(self):
        return len(self.client)

