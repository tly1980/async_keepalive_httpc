import os
import uuid
import json

import yaml
from tornado.testing import AsyncTestCase, gen_test
import boto.dynamodb

from async_keepalive_httpc.aws.dynamodb import DynamoDB


class DynamoDBTestCase(AsyncTestCase):
    type_key = 'unittesting'
    endpoint = 'ap-southeast-2'

    test_data = [
        {'a': 123, 'b': 456},
        {'foo': 9123, 'bar': 9456},
    ]

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

        self.boto_db = boto.dynamodb.connect_to_region(
            self.endpoint,
            aws_access_key_id=self.ACCESS_KEY,
            aws_secret_access_key=self.SECRET_KEY)

        self.test_table = self.boto_db.get_table('DEV_USER_DATA')

        self.test_keys = [str(uuid.uuid4()) for i in xrange(len(self.test_data))]

        self.items = []

        for k, d in zip(self.test_keys, self.test_data):
            item_data = {
              'DATA': json.dumps(d)
            }

            item  = self.test_table.new_item(
                hash_key=k,
                range_key=self.type_key,
                attrs=item_data
            )

            item.put()
            self.items.append(item)

    @gen_test(timeout=100)
    def test_get_item(self):

        resp = None
        self.callback_data = None

        db = DynamoDB(
            self.io_loop,
            self.ACCESS_KEY,
            self.SECRET_KEY)
        
        for k, d in zip(self.test_keys, self.test_data):
            resp = yield db.get_item('DEV_USER_DATA', 
                {
                    'USER_ID': {'S': k}, 
                    'TYPE': {'S': self.type_key}, 
                }, 
                attributes_to_get = ['DATA'],
            )

            self.assertEqual(d, json.loads(resp.aws_result['Item']['DATA']['S']))

