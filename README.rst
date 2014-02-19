=============================
 Async Keep-Alive Http Client
=============================
:Info: See <https://github.com/tly1980/async_keepalive_httpc> for introductory docs.
:Author: Tom Tang <tly1980@gmail.com>
:Date: .. |date|
:Description: Async Keep-Alive Http Client

Keep-alive_ is a well-known and popular technique to reduce the latencies and speed up the resource retrival.
(See <http://chimera.labs.oreilly.com/books/1230000000545/ch11.html#BENEFITS_OF_KEEPALIVE>)

It allows one connection to request multiple resources, which can avoid
the penalties of establishing and closing a HTTP connection, and quite significantly for HTTPS connection.

Tornado_ is highly efficient Python asynchronous web framework & network libary. 
and I am quite enjoying using to build high performance web application.
However, Tornado_ does not ship with a httpclient that support Keep-alive out of box up to now (v3.1.1 October, 2013.)

And that is exactly why I created this libaray, which comes with a HTTP client that supports Keep-Alive feature.
This client is basically a hack of tornado Httpclient and HttpConnection, so the API is very much the same, 
which means it can use Tornado HTTPRequest and most feature of the original client 
(like gzip, proxies, .etc - Warrning: further tests needed to be conducted for this features.).

A Proxy_ feature is included since version 0.13. The proxy implementation is using pycurl, so the the Keep-Alive feature would be disabled. 

Besides that, the libaray also provide a Queue Function limited support to some of the AWS services: SQS and DyanmoDB.
And, last but not least, a simple resource pool.

.. _Tornado: http://www.tornadoweb.org/en/stable

.. _Keep-alive: http://en.wikipedia.org/wiki/HTTP_persistent_connection

.. technique_: http://chimera.labs.oreilly.com/books/1230000000545/ch11.html#BENEFITS_OF_KEEPALIVE

.. _Proxy: http://en.wikipedia.org/wiki/Proxy_server


Example
=======
.. code-block:: python
 
 from async_keepalive_httpc.keepalive_client import SimpleKeepAliveHTTPClient
 
 
 ska_client = SimpleKeepAliveHTTPClient(self.io_loop)
 
 # just assume that you have a http server that supports connection keep-alive and
 # it has a.txt which just has a simple text 'aaa'. Accordingly, b.txt has a simple text
 # 'bbb', so is 'ccc' in c.txt
 
 a, b, c = yield [
    ska_client.fetch('http://localhost/a.txt'),
    ska_client.fetch('http://localhost/b.txt'),
    ska_client.fetch('http://localhost/c.txt'),
 ]
 
 assert 'aaa' in a.body
 assert 'bbb' in b.body
 assert 'ccc' in c.body
 
 # The client should fetch them using just one connection, 
 # rather than disconnect and connect reapeatly.
 assert ska_client.connection.connect_times == 1
 
 
===========
AWS Support
===========

SQS
===

.. code-block:: python

 from async_keepalive_httpc.aws.sqs import SQSQueue

 q = SQSQueue(
     io_loop,
     'AWS_ACCESS_KEY',
     'AWS_SECRET_KEY',
     'https://ap-southeast-2.queue.amazonaws.com/YOUR_ACCOUNT_NUMBER/YOUR_QUEUE_NAME',
     endpoints='ap-southeast-2')

 r1 = yield q.send('abc')
 r2 = yield q.send('cde')
 r3 = yield q.send('fgh')

 assert r1.code == 200
 assert r2.code == 200
 assert r3.code == 200

 # make sure it is 'keep-alive'
 assert q.client.connection.connect_times == 1
 

DynamoDB
========

.. code-block:: python
 
 from async_keepalive_httpc.aws.dynamodb import DynamoDB
 
 db = DynamoDB(
     self.io_loop,
     'AWS_ACCESS_KEY',
     'AWS_SECRET_KEY',
     endpoints='ap-southeast-2')
 
 resp = yield db.get_item('TEST_USER_DATA', 
     {
         'USER_ID': {'S':'EEB750F4-C589-4C0A-95C3-C1B572A0CC3E'}, 
     }, 
     attributes_to_get = ['Name']
 )

 print resp.aws_result


Output would be something like:

.. code-block:: python

 {
   'Item': { 
      'DATA': { 
        'S': 'Tom Cruse'
      }
   }
 }


Resource Pool
=============

.. code-block:: python

 from tornado.testing import AsyncTestCase, gen_test
 from async_keepalive_httpc.keepalive_client import SimpleKeepAliveHTTPClient
 from async_keepalive_httpc.pool import ResourcePool
 
 
 class ResourcePoolTestCase(AsyncTestCase):
 
     @gen_test
     def test_basic(self):
         create_func = lambda: SimpleKeepAliveHTTPClient(self.io_loop)
         pool = ResourcePool(create_func, init_count=2, max_count=3)
 
         self.assertEqual(len(pool._pool), 2)
         ska_client1 = pool.get()
         ska_client1.fetch('http://www.google.com')
         ska_client2 = pool.get()
 
         self.assertNotEqual(ska_client1, ska_client2)
 
         ska_client2.fetch('http://www.google.com')
 
         ska_client3 = pool.get()
 
         ska_client3.fetch('http://www.google.com')
 
         self.assertNotEqual(ska_client1, ska_client3)
         self.assertNotEqual(ska_client2, ska_client3)
 
         ska_client2.fetch('http://www.google.com')
         ska_client3.fetch('http://www.google.com')
 
         ska_client4 = pool.get()
         self.assertEqual(ska_client1, ska_client4)

Using Proxy
===========

.. code-block:: python

 from async_keepalive_httpc.aws.sqs import SQSQueue

 PROXY_CONFIG = {
   'proxy_host': 'localhost',
   'proxy_port': 3128,
 }

 sqs = SQSQueue(io_loop,
                Q_URL,
                access_key = self.ACCESS_KEY,
                secret_key= self.SECRET_KEY,
                proxy_config=PROXY_CONFIG)
 
 yield sqs.send('my msg via proxy')

