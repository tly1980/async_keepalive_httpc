import os
import yaml
from tornado.testing import AsyncTestCase, gen_test
from async_keepalive_httpc.aws.sqs import SQSQueue


class SQSTest(AsyncTestCase):

    def setUp(self):
        super(SQSTest, self).setUp()
        path = os.path.abspath(
            os.path.join (
                os.path.dirname(__file__), 'aws_keypair.yaml' 
            )
        )

        with open(path, 'rb') as f:
            d = yaml.load(f.read())
            self.Q_URL = d['Q_URL']
            self.ACCESS_KEY = d['ACCESS_KEY']
            self.SECRET_KEY = d['SECRET_KEY']

    @gen_test(timeout=100)
    def test_send(self):
        q = SQSQueue(
            self.io_loop,
            self.ACCESS_KEY,
            self.SECRET_KEY,
            self.Q_URL)

        r1 = yield q.send('abc')
        r2 = yield q.send('cde')
        r3 = yield q.send('fgh')

        self.assertEqual(r1.code, 200)
        self.assertEqual(r2.code, 200)
        self.assertEqual(r3.code, 200)

        # make sure it is 'keep-alive'
        self.assertEqual(q.client.connection.connect_times, 1)
