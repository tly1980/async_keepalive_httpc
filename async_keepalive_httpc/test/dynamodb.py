import os
import yaml
from tornado.testing import AsyncTestCase, gen_test
from async_keepalive_httpc.aws.dynamodb import DynamoDB


class DynamoDBTestCase(AsyncTestCase):

    def setUp(self):
        super(DynamoDBTestCase, self).setUp()
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
    def test_get_item(self):

        resp = None
        self.callback_data = None

        def xtract_item(d, error=None, response=None):
            self.assertEqual(response.aws_result, d)
            self.callback_data = d

        db = DynamoDB(
            self.io_loop,
            self.ACCESS_KEY,
            self.SECRET_KEY)
        
        resp = yield db.get_item('TEST_USER_DATA', 
            {
                'USER_ID': {'S':'fed41051c8b49892c3107e1f6faa1644'}, 
                'TYPE': {'N': '0'}, 
            }, 
            attributes_to_get = ['LOCATION'],
            callback=xtract_item
        )

        self.assertEqual(self.callback_data, resp.aws_result)

