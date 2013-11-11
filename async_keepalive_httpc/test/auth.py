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

    def test_sign_get(self):
        ACCESS_KEY = 'AKIDEXAMPLE'
        SECRET_KEY = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
        
        v4sign = EasyV4Sign(
            ACCESS_KEY, 
            SECRET_KEY,
            'host',
            endpoint='us-east-1',
        )

        timestamp = '20110909T233600Z'

        headers = {'Date':'Mon, 09 Sep 2011 23:36:00 GMT'}
        x_method, x_url, x_headers, x_body = v4sign.sign_get(
            'http://host.foo.com', headers, params={}, timestamp=timestamp)
        
        self.assertNotEqual(x_headers, headers)

        self.assertTrue('b27ccfbfa7df52a200ff74193ca6e32d4b48b8856fab7ebf1c595d0670a7e470' in
            x_headers['Authorization'])

    def test_sign_post(self):
        ACCESS_KEY = 'AKIDEXAMPLE'
        SECRET_KEY = "wJalrXUtnFEMI/K7MDENG+bPxRfiCYEXAMPLEKEY"
        
        v4sign = EasyV4Sign(
            ACCESS_KEY, 
            SECRET_KEY,
            'iam',
            endpoint='us-east-1',
        )

        timestamp = '20110909T233600Z'

        headers = {'Content-type': 'application/x-www-form-urlencoded; charset=utf-8'}
        data = {
            'Version': '2010-05-08',
            'Action': 'ListUsers'
        }
        x_method, x_url, x_headers, x_body = v4sign.sign_post(
            'http://iam.amazonaws.com/', headers, data=data, timestamp=timestamp)
        
        self.assertNotEqual(x_headers, headers)

        self.assertTrue('ced6826de92d2bdeed8f846f0bf508e8559e98e4b0199114b84c54174deb456c' in
            x_headers['Authorization'])


