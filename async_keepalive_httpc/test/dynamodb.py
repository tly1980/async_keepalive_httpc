import os
import uuid
import json

import yaml
from tornado.testing import AsyncTestCase, gen_test
import boto.dynamodb

from async_keepalive_httpc.aws.dynamodb import DynamoDB
from async_keepalive_httpc.aws.auth import IamRoleV4Sign

class DynamoDBTestCase(AsyncTestCase):
    type_key = 'unittesting'
    _region = 'ap-southeast-2'
    _table_name = 'UT_USER_DATA'

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

        is_using_meta = False

        if os.path.isfile(path):
            with open(path, 'rb') as f:
                d = yaml.load(f.read())
                self.Q_URL = d['Q_URL']
                self.ACCESS_KEY = d['ACCESS_KEY']
                self.SECRET_KEY = d['SECRET_KEY']

            self.boto_db = boto.dynamodb.connect_to_region(
                self._region,
                aws_access_key_id=self.ACCESS_KEY,
                aws_secret_access_key=self.SECRET_KEY)


        else:
            is_using_meta = True
            self.boto_db = boto.dynamodb.connect_to_region(
                self._region)
        try:
            self.test_table = self.boto_db.get_table(self._table_name)
        except:
            _schema = self.boto_db.create_schema(
                hash_key_name='USER_ID',
                hash_key_proto_value=str,
                range_key_name='TYPE',
                range_key_proto_value=str
                )
            self.test_table = self.boto_db.create_table(
                name=self._table_name,
                schema=_schema,
                read_units=1, write_units=1)

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

        if not is_using_meta:
            self.db = DynamoDB(
                self.io_loop,
                access_key=self.ACCESS_KEY,
                secret_key=self.SECRET_KEY,
                region=self._region)
        else:
            signer = IamRoleV4Sign(
                self.io_loop,
                'dynamodb',
                region = self._region
            )

            self.db = DynamoDB(
                self.io_loop,
                signer=signer,
                region=self._region)


    @gen_test(timeout=100)
    def test_get_item(self):

        resp = None
        self.callback_data = None


        
        for k, d in zip(self.test_keys, self.test_data):
            resp = yield self.db.get_item(
                self._table_name, 
                {
                    'USER_ID': {'S': k}, 
                    'TYPE': {'S': self.type_key}, 
                }, 
                attributes_to_get = ['DATA'],
            )

            self.assertEqual(d, json.loads(resp.aws_result['Item']['DATA']['S']))

