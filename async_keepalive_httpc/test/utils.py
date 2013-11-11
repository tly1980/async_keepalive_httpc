import unittest
from async_keepalive_httpc.utils import UrlInfo


class UrlInfoTest(unittest.TestCase):
    def test_http(self):
        urlinfo = UrlInfo('http://LOCALHOST/abc?a=23&b=456')
        self.assertEqual(urlinfo.host, 'localhost')
        self.assertEqual(urlinfo.port, 80)
        self.assertEqual(urlinfo.is_ssl, False)
        self.assertEqual(urlinfo.uri_with_query, '/abc?a=23&b=456')
        self.assertEqual(urlinfo.connection_key, 'http://localhost:80')

    def test_https(self):
        urlinfo = UrlInfo('https://localhost/abc')
        self.assertEqual(urlinfo.port, 443)
        self.assertEqual(urlinfo.is_ssl, True)
        self.assertEqual(urlinfo.is_ssl, True)
        self.assertEqual(urlinfo.connection_key, 'https://localhost:443')

    def test_https_port(self):
        urlinfo = UrlInfo('https://localhost:9443/abc')
        self.assertEqual(urlinfo.port, 9443)
        self.assertEqual(urlinfo.is_ssl, True)
        self.assertEqual(urlinfo.is_ssl, True)
        self.assertEqual(urlinfo.connection_key, 'https://localhost:9443')