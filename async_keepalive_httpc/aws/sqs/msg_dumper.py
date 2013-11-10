import os
import argparse
import csv
import logging
import yaml
import functools
import traceback
import urllib
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
        'verbosity': 'INFO',
        'ap-southeast-2': 'ap-southeast-2'
    }

    config = dict(default_config)

    with open(config_path, 'rb') as f:
        config_read = yaml.load(f.read())
        config.update(**config_read)
    level = getattr(logging, config.get('verbosity', 'INFO'))
    logging.basicConfig(level=level)
    return config


def extract_xml(request, messages=[], callback=None):
    the_resp = None
    if request.resp_code != 200:
        sqs_recv_logger.warn("resp body: \n%s" % request.resp_data)
        sqs_recv_logger.warn("orig req: \n%s" % request.req())
    else:
        the_resp = xmltodict.parse(request.resp_data)
        sqs_recv_logger.info("{} messages removed".format(len(messages)))


    if callback:
        callback(request, the_resp)


class CsvWriter(object):
    def __init__(self, *args, **kwargs):
        self.the_file = kwargs.get('the_file')
        self.writer = csv.writer(self.the_file, delimiter='\t',
            quotechar='|', quoting=csv.QUOTE_MINIMAL)

    def write_row(self, message_id, timestamp, message_content):
        self.writer.writerow([message_id, timestamp, message_content])
        self.the_file.flush()


class App(object):
    check_feq_sec = 0.1

    def __init__(self, *args, **kwargs):
        self.access_key = kwargs.get('access_key')
        self.secret_key = kwargs.get('secret_key')
        self.endpoint = kwargs.get('endpoint')
        self.io_loop = kwargs.get('io_loop', 
            tornado.ioloop.IOLoop.instance())
        self.q_url = kwargs.get('q_url')
        self.q_url_info = UrlInfo(self.q_url)
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

        self.logger = logging.getLogger(App.__class__.__name__)

    @gen.coroutine
    def check(self):
        req = yield gen.Task(self.receiver.receive)
        messages = req.sqs_messages

        for m in messages:
            self.csv_writer.write_row(m['MessageId'], m['Body'], m['ReceiptHandle'])

        if self.delete_after_dump and messages:
            self.logger.info('got {} messages, about to remove them from q'.format(len(messages)))
            yield gen.Task(self.remove_messages, messages)

        self.io_loop.add_callback(self.check)

    def run(self):
        self.io_loop.add_callback(self.check)
        self.io_loop.start()


    def remove_messages(self, messages, callback=None):
        
        data = {
            'Action': 'DeleteMessageBatch',
            'Version': '2011-10-01',
        }

        i = 1
        for m in messages:
            data['DeleteMessageBatchRequestEntry.{}.Id'.format(i)] = urllib.quote_plus(m['MessageId'])
            data['DeleteMessageBatchRequestEntry.{}.ReceiptHandle'.format(i)] = urllib.quote_plus(m['ReceiptHandle'])
            i += 1

        try:
            x_method, x_url, x_headers, x_body = self.v4sign.sign_post(
                self.q_url, {}, data=data)

            cb = functools.partial(extract_xml, messages=messages, callback=callback)
        except Exception, e:
            self.logger.exception(e)


        r = Request(UrlInfo(x_url), method="POST", 
                callback=cb, extra_headers=x_headers, body=x_body)
        self.sq_mgr_rm_msg.add(r)



if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', help="config file", type=str, default='./config.yaml')
    args = parser.parse_args()

    config_path = real_path_to_cwd(args.config)
    config = load_config(config_path)
    config_msg_dumper = config['msg_dumper']
    app = App(**config_msg_dumper)
    app.run()


