

class SQSDumper(object):
    def __init__(self, 
        access_key, secret_key, q_url, 
        endpoint='ap-southeast-2',
        max_connection=4, io_loop=tornado.ioloop.IOLoop.instance()):
        self.q_url_info = UrlInfo(q_url)
        self.q_url = q_url
        self.ka_httpc_pool = KeepAlivePool(
            self.q_url_info.host,
            port=self.q_url_info.port,
            is_ssl=self.q_url_info.is_ssl,
            init_count=1,
            max_count=max_connection,
            io_loop=io_loop)
        self.logger = logging.getLogger(Sender.__class__.__name__)
        self.access_key = access_key
        self.secret_key = secret_key



