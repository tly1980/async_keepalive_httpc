=============================
 Async Keep-Alive Http Client
=============================
:Info: See <https://github.com/tly1980/async_keepalive_httpc> for introductory docs.
:Author: Tom Tang <tly1980@gmail.com>
:Date: .. |date|
:Description: Async Keep-Alive Http Client



This libaray comes with a HTTP client that supports Keep-Alive feature.
Besides that, the libaray also provide a limited support to some of the AWS services: SQS and DyanmoDB.

.. code-block:: python

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
 
