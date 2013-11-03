import os
import datetime

from tornado import gen
import yaml
from tornado.testing import AsyncTestCase, gen_test


from async_keepalive_httpc.aws.sqs import Sender


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
        sender = Sender(
            self.ACCESS_KEY,
            self.SECRET_KEY,
            self.Q_URL,
            max_connection=1,
            io_loop=self.io_loop)

        a, b, c = yield [
            gen.Task(sender.send, 'test1'),
            gen.Task(sender.send, 'test2        askdjfhjka jkdshfkj \nsdfsdf\nsdfsdf\n'),
            gen.Task(sender.send, 'test3'),
        ]

        self.fail('sdf')
