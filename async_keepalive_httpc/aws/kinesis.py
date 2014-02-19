import logging
import functools
import base64

from tornado.httpclient import HTTPRequest

from async_keepalive_httpc.utils import json
from async_keepalive_httpc.aws.common import AWSClient

logging.basicConfig(level=logging.DEBUG)

class KinesisAPI(object):
    def default_callback(self, data, error=None, response=None):
        self.logger.debug('data: {}'.format(data))

    def put_record(self, stream_name, data, partion_key, 
            explicit_hash_key=None, sequence_number_for_ordering=None, 
            exclusive_minimum_sequence_number=None, b64_encode=True,
            callback=None, object_hook=None):
        api_data = {
            'StreamName': stream_name,
            'PartitionKey': str(partion_key)
        }

        if exclusive_minimum_sequence_number: 
            api_data['SequenceNumberForOrdering'] = str(exclusive_minimum_sequence_number)

        if explicit_hash_key: 
            api_data['ExplicitHashKey'] = str(explicit_hash_key)

        if b64_encode:
            api_data['Data'] = base64.b64encode(data)
        else:
            api_data['Data'] = data

        return self.make_request('PutRecord', api_data,
            callback=callback, object_hook=object_hook)
        

    def make_request(self, action, data, callback=None, object_hook=None):
        '''
        Make an asynchronous HTTP request to DynamoDB. Callback should operate on
        the decoded json response (with object hook applied, of course). It should also
        accept an error argument, which will be a boto.exception.DynamoDBResponseError.
        
        If there is not a valid session token, this method will ensure that a new one is fetched
        and cache the request when it is retrieved. 
        '''

        headers = {
            'X-Amz-Target':  '%s_%s.%s' % (self._service, self._version, action),
            'Content-Type' : 'application/x-amz-json-1.1'
        }

        x_method, x_url, x_headers, x_body = self.v4sign.sign_json(
            self.url, headers, data=data)

        r = HTTPRequest(self.url, method=x_method, headers=x_headers, body=x_body)

        if not callback:
            callback = self.default_callback

        callback = functools.partial(self._finish_make_request,
            callback=callback, object_hook=object_hook)

        return self.fire(r, callback=callback)


    def _finish_make_request(self, response, callback, object_hook=None):
        '''
        Check for errors and decode the json response (in the tornado response body), then pass on to orig callback.
        This method also contains some of the logic to handle reacquiring session tokens.
        '''

        if object_hook:
            try:
                json_response = json.loads(response.body, object_hook=object_hook)
            except TypeError:
                json_response = None
        else:
            try:
                json_response = json.loads(response.body)
            except TypeError:
                json_response = None

        if json_response and response.error:
            return callback(json_response, error=response.error, response=response)
        response.aws_result = json_response
        return callback(json_response, error=None, response=response)


class Kinesis(KinesisAPI, AWSClient):
    _service = 'Kinesis'
    _version = '20131202'

    def __init__(self,  io_loop, is_ssl=False, **kwargs):

        super(Kinesis, self).__init__(io_loop, **kwargs)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_ssl = is_ssl

        if self.is_ssl:
            self.url = 'https://kinesis.{}.amazonaws.com/'.format(self.region)
        else:
            self.url = 'http://kinesis.{}.amazonaws.com/'.format(self.region)
