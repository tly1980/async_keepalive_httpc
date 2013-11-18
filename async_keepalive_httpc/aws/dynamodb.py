import logging
from tornado.httpclient import HTTPRequest

from async_keepalive_httpc.utils import json
from async_keepalive_httpc.aws.common import AWSClient
import functools


class DynamoAPI(object):
    """
    This class is modified from bitly asyncdynamo
    https://github.com/bitly/asyncdynamo/blob/master/asyncdynamo/asyncdynamo.py 
    """

    def default_callback(self, data, error=None, response=None):
        self.logger.debug('data: {}'.format(data))


    def make_request(self, action, data, callback=None, object_hook=None):
        '''
        Make an asynchronous HTTP request to DynamoDB. Callback should operate on
        the decoded json response (with object hook applied, of course). It should also
        accept an error argument, which will be a boto.exception.DynamoDBResponseError.
        
        If there is not a valid session token, this method will ensure that a new one is fetched
        and cache the request when it is retrieved. 
        '''


        headers = {'X-Amz-Target':
            '%s_%s.%s' % (self._service, self._version, action),
            'Content-Type' : 'application/x-amz-json-1.0'
        }

        x_method, x_url, x_headers, x_body = self.v4sign.sign_json(
            self.url, headers, data=data)

        r = HTTPRequest(self.url, method=x_method, headers=x_headers, body=x_body)

        callback = functools.partial(self._finish_make_request,
            callback=callback, object_hook=object_hook)

        return self.client.fetch(r, callback=callback)

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

    def get_item(self, table_name, key, callback=None, attributes_to_get=None,
            consistent_read=False, object_hook=None):
        '''
        Return a set of attributes for an item that matches
        the supplied key.
        
        The callback should operate on a dict representing the decoded
        response from DynamoDB (using the object_hook, if supplied)
        
        :type table_name: str
        :param table_name: The name of the table to delete.

        :type key: dict
        :param key: A Python version of the Key data structure
            defined by DynamoDB.

        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type consistent_read: bool
        :param consistent_read: If True, a consistent read
            request is issued.  Otherwise, an eventually consistent
            request is issued.        '''
        data = {'TableName': table_name,
                'Key': key}
        if attributes_to_get:
            data['AttributesToGet'] = attributes_to_get
        if consistent_read:
            data['ConsistentRead'] = True

        if not callback:
            callback = self.default_callback

        return self.make_request('GetItem', data,
            callback=callback, object_hook=object_hook)
    
    def batch_get_item(self, request_items, callback):
        """
        Return a set of attributes for a multiple items in
        multiple tables using their primary keys.
        
        The callback should operate on a dict representing the decoded
        response from DynamoDB (using the object_hook, if supplied)

        :type request_items: dict
        :param request_items: A Python version of the RequestItems
            data structure defined by DynamoDB.
        """
        data = {'RequestItems' : request_items}

        self.make_request('BatchGetItem', data, callback)
        
    def put_item(self, table_name, item, callback, expected=None, return_values=None, object_hook=None):
        '''
        Create a new item or replace an old item with a new
        item (including all attributes).  If an item already
        exists in the specified table with the same primary
        key, the new item will completely replace the old item.
        You can perform a conditional put by specifying an
        expected rule.
        
        The callback should operate on a dict representing the decoded
        response from DynamoDB (using the object_hook, if supplied)

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type item: dict
        :param item: A Python version of the Item data structure
            defined by DynamoDB.

        :type expected: dict
        :param expected: A Python version of the Expected
            data structure defined by DynamoDB.

        :type return_values: str
        :param return_values: Controls the return of attribute
            name-value pairs before then were changed.  Possible
            values are: None or 'ALL_OLD'. If 'ALL_OLD' is
            specified and the item is overwritten, the content
            of the old item is returned.        
        '''
        data = {'TableName' : table_name,
                'Item' : item}
        if expected:
            data['Expected'] = expected
        if return_values:
            data['ReturnValues'] = return_values

        return self.make_request('PutItem', data, callback=callback,
                                 object_hook=object_hook)
    
    def query(self, table_name, hash_key_value, callback, range_key_conditions=None,
              attributes_to_get=None, limit=None, consistent_read=False,
              scan_index_forward=True, exclusive_start_key=None,
              object_hook=None):
        '''
        Perform a query of DynamoDB.  This version is currently punting
        and expecting you to provide a full and correct JSON body
        which is passed as is to DynamoDB.
        
        The callback should operate on a dict representing the decoded
        response from DynamoDB (using the object_hook, if supplied)

        :type table_name: str
        :param table_name: The name of the table to delete.

        :type hash_key_value: dict
        :param key: A DynamoDB-style HashKeyValue.

        :type range_key_conditions: dict
        :param range_key_conditions: A Python version of the
            RangeKeyConditions data structure.

        :type attributes_to_get: list
        :param attributes_to_get: A list of attribute names.
            If supplied, only the specified attribute names will
            be returned.  Otherwise, all attributes will be returned.

        :type limit: int
        :param limit: The maximum number of items to return.

        :type consistent_read: bool
        :param consistent_read: If True, a consistent read
            request is issued.  Otherwise, an eventually consistent
            request is issued.

        :type scan_index_forward: bool
        :param scan_index_forward: Specified forward or backward
            traversal of the index.  Default is forward (True).

        :type exclusive_start_key: list or tuple
        :param exclusive_start_key: Primary key of the item from
            which to continue an earlier query.  This would be
            provided as the LastEvaluatedKey in that query.
        '''
        data = {'TableName': table_name,
                'HashKeyValue': hash_key_value}
        if range_key_conditions:
            data['RangeKeyCondition'] = range_key_conditions
        if attributes_to_get:
            data['AttributesToGet'] = attributes_to_get
        if limit:
            data['Limit'] = limit
        if consistent_read:
            data['ConsistentRead'] = True
        if scan_index_forward:
            data['ScanIndexForward'] = True
        else:
            data['ScanIndexForward'] = False
        if exclusive_start_key:
            data['ExclusiveStartKey'] = exclusive_start_key
        #json_input = json.dumps(data)
        return self.make_request('Query', data,
                                 callback=callback, object_hook=object_hook)


class DynamoDB(DynamoAPI, AWSClient):
    _service = 'DynamoDB'
    _version = "20120810"

    def __init__(self,  io_loop, access_key, secret_key, endpoint='ap-southeast-2', is_ssl=False):
        super(DynamoDB, self).__init__(
            io_loop, access_key, secret_key, endpoint)
        self.logger = logging.getLogger(self.__class__.__name__)
        self.is_ssl = is_ssl
        if self.is_ssl:
            self.url = 'https://dynamodb.{}.amazonaws.com/'.format(self.endpoint)
        else:
            self.url = 'http://dynamodb.{}.amazonaws.com/'.format(self.endpoint)
