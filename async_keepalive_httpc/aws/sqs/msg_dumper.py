import os
import argparse
import csv
import logging
import yaml
import functools

import tornado
import tornado.ioloop
from tornado import gen
import xmltodict

from async_keepalive_httpc.aws.sqs import Receiver
from async_keepalive_httpc.request import QueueManager, Request, UrlInfo
from async_keepalive_httpc.aws.auth import EasyV4Sign

sqs_recv_logger = logging.getLogger("sqs_recv")

def real_path_to_cwd(path):
    ret_path = path
    cwd = os.getcwd()
    if not path.startswith('/'):
        ret_path = os.path.abspath(
            os.path.join(cwd, path)
        )
    return ret_path


def load_config(config_path):
    default_config = {
        'verbosity': 'INFO'
    }

    config = dict(default_config)

    with open(config_path, 'rb') as f:
        config_read = yaml.load(f.read())
        config.update(**config_read)
    level = getattr(logging, config.get('verbosity', 'INFO'))
    logging.basicConfig(level=level)
    return config


def extract_xml(request, callback=None):
    the_resp = None
    if request.resp_code != 200:
        sqs_recv_logger.warn("resp body: \n%s" % request.resp_data)
        sqs_recv_logger.warn("orig req: \n%s" % request.req())
    else:
        the_resp = xmltodict.parse(request.resp_data)

    if callback:
        callback(request, the_resp)


class CsvWriter(object):
    def __init__(self, *args, **kwargs):
        self.the_file = kwargs.get('the_file')
        self.writer = csv.writer(self.the_file, delimiter='\t',
            quotechar='|', quoting=csv.QUOTE_MINIMAL)

    def write_row(self, message_id, timestamp, message_content):
        self.writer.write([message_id, timestamp, message_content])
        self.the_file.flush()


class App(object):
    def __init__(self, *args, **kwargs):
        self.access_key = kwargs.get('access_key')
        self.secret_key = kwargs.get('secret_key')
        self.io_loop = kwargs.get('io_loop', 
            tornado.ioloop.IOLoop.instance())
        self.q_url = kwargs.get('q_url')
        file_path = real_path_to_cwd(kwargs.get('dump_file', './message.csv'))
        the_file = open(file_path, 'ab')
        self.csv_writer = CsvWriter(the_file=the_file)
        self.delete_after_dump = kwargs.get('delete_after_dump', True)
        self.v4sign = EasyV4Sign(
            self.access_key, self.secret_key,
            'sqs',
            endpoint=self.endpoint
        )

        self.sq_mgr_rm_msg = QueueManager(
            self.io_loop,
            self.q_url_info.host,
            self.q_url_info.port,
            self.q_url_info.is_ssl,
        )


        self.receiver = Receiver(
            self.access_key,
            self.secret_key,
            self.q_url)


    def run(self):
        while(True):
            req, messages = yield gen.Task(self.receiver.receive)

            for m in messages:
                self.csv_writer.write_row(m['message_id'], m['timestamp'], m['message_content'])

            if self.delete_after_dump:
                yield gen.Task(self.remove_messages, messages)

    def remove_messages(self, messages, callback=None):
        params = {
            'Action': 'DeleteMessageBatch',
            'Version': '2011-10-01',
        }

        i = 1
        for m in messages:
            params['DeleteMessageBatchRequestEntry.{}.id'.format(i)] = m['id']
            params['DeleteMessageBatchRequestEntry.{}.ReceiptHandle'.format(i)] = m['ReceiptHandle']
            i += 1

        x_method, x_url, x_headers, x_body = self.v4sign.sign_get(
            self.q_url, self._header_tpl, params=params)

        cb = functools.partial(extract_xml, callback=callback)

        r = Request(UrlInfo(x_url), method="GET", 
                callback=cb, extra_headers=x_headers, body=x_body)
        self.sq_mgr.add(r)


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help="config file", type=str, default='./config.yaml')
    args = parser.parse_args()

    config_path = real_path_to_cwd(args.config)
    config = load_config(config_path)
    config_msg_dumper = config['msg_dumper']
    app = App(**config)
    app.run()

