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


    def test_sign_post(self):
        ACCESS_KEY = 'AKIDEXAMPLE'
        SECRET_KEY = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
        
        v4sign = EasyV4Sign(
            ACCESS_KEY, 
            SECRET_KEY,
            'host',
            endpoint='us-east-1',
        )

        timestamp = '20110909T233600Z'

        params = {
             'foo': 'ListUsers',
             'Version': '2010-05-08'
        }

        x_method, x_url, x_headers, x_body = v4sign.sign_get(
            self.Q_URL, params=params, timestamp=timestamp)


