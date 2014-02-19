import os
import functools

import yaml
from tornado.testing import AsyncTestCase, gen_test
import async_keepalive_httpc.aws.kinesis
from async_keepalive_httpc.aws.auth import IamRoleV4Sign


if os.environ.get('PROXY_HOST'):
    PROXY_CONFIG = dict(
        zip(
            ['proxy_host', 'proxy_port'],
            [os.environ.get('PROXY_HOST'), int(os.environ.get('PROXY_PORT'))]
        )
    )
else:
    PROXY_CONFIG = {}


class KinesisTestCase(AsyncTestCase):

    _region = 'us-east-1'
    _stream_name = 'UT_Kinesis1'


    _Kinesis = functools.partial(
        async_keepalive_httpc.aws.kinesis.Kinesis, 
        use_curl=False, 
        is_ssl=True
    )

    def setUp(self):
        super(KinesisTestCase, self).setUp()
        path = os.path.abspath(
            os.path.join (
                os.path.dirname(__file__), 'aws_keypair.yaml' 
            )
        )

        is_using_meta = False

        if os.path.isfile(path):
            with open(path, 'rb') as f:
                d = yaml.load(f.read())
                #self.Q_URL = d['Q_URL']
                self.ACCESS_KEY = d['ACCESS_KEY']
                self.SECRET_KEY = d['SECRET_KEY']

        else:
            is_using_meta = True

        if not is_using_meta:
            self.k = self._Kinesis(
                self.io_loop,
                access_key=self.ACCESS_KEY,
                secret_key=self.SECRET_KEY,
                region=self._region)
        else:
            signer = IamRoleV4Sign(
                self.io_loop,
                'kinesis',
                region = self._region
            )

            self.k = self._Kinesis(
                self.io_loop,
                signer=signer,
                region=self._region)

    @gen_test(timeout=10000)
    def test_put_record(self):
    	r = yield self.k.put_record(self._stream_name, 'testA', 1)
    	self.assertIsNotNone(r)
    	self.assertTrue('SequenceNumber' in r.aws_result)
