import urlparse

try:
    import ujson as json
except:
    import json

class UrlInfo(object):
    def __init__(self, url):
        self.p = urlparse.urlparse(url)

    @property
    def uri(self):
        return self.p.path 

    @property
    def uri_with_query(self):
        if self.p.query:
            return self.p.path + '?' + self.p.query
        else:
            return self.p.path


    @property
    def port(self):
        if self.p.port:
            return self.p.port

        if self.p.scheme.lower() == 'http':
            return 80

        if self.p.scheme.lower() == 'https':
            return 443

    @property
    def host(self):
        return self.p.hostname.lower()

    @property
    def is_ssl(self):
        return 's' in self.p.scheme.lower()

    @property
    def connection_key(self):
        return '{}://{}:{}'.format(self.p.scheme.lower(), self.host, self.port)
