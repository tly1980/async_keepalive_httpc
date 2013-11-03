import unittest
import os
import yaml
import time

from async_keepalive_httpc.aws.auth import EasyV4Sign


class EasyV4SignTest(unittest.TestCase):

    def setUp(self):
        super(EasyV4SignTest, self).setUp()
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

    # def test_sign_iam(self):
    #     v4sign = EasyV4Sign(
    #         self.ACCESS_KEY, self.SECRET_KEY,
    #         'iam',
    #         endpoint='us-east-1'
    #     )

    #     headers = { 
    #         'Content-type':'application/x-www-form-urlencoded; charset=utf-8'
    #     }

    #     params = {
    #         'Action': 'ListUsers',
    #         'Version': '2010-05-08'
    #     }

    #     x_method, x_url, x_headers, x_body = ev4sign.sign(
    #         url, headers, params=params, 
    #         method='POST', timestamp=self.TIMESTAMP
    #     )





    def test_sign(self):
        v4sign = EasyV4Sign(
            self.ACCESS_KEY, self.SECRET_KEY,
            'sqs',
            endpoint='ap-southeast-2',
        )

        timestamp = '20131103T042039Z'

        query = {
            'Action': 'SendMessage', 
            'MessageBody': 'msg1',
            'Version': '2012-11-05',
        }

        headers = { 
            'Content-type':'application/x-www-form-urlencoded; charset=utf-8'
        }

        l = ['='.join([k, query[k]]) for k in sorted(query.keys())]
        body = '&'.join(l)


        x_method, x_url, x_headers, x_body = v4sign.sign(
            self.Q_URL, headers, body, method='POST', timestamp=timestamp)

        self.fail('aa')

        

