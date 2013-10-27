#!/usr/bin/env python

import tornado.ioloop
import tornado.iostream
import socket


def send_request():
    stream.write(b"GET /a.txt HTTP/1.1\r\nHost: localhost\r\n\r\n")
    stream.read_until(b"\r\n\r\n", on_headers)

def on_headers(data):
    headers = {}
    for line in data.split(b"\r\n"):
       parts = line.split(b":")
       if len(parts) == 2:
           headers[parts[0].strip()] = parts[1].strip()
    #import ipdb; ipdb.set_trace()
    stream.read_bytes(int(headers[b"Content-Length"]), on_body)

def on_body(data):
    print data
    stream.close()
    tornado.ioloop.IOLoop.instance().stop()

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM, 0)


stream = tornado.iostream.SSLIOStream(s)
stream.connect(("localhost", 9443), send_request)
tornado.ioloop.IOLoop.instance().start()

