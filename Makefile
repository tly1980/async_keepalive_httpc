.PHONY: build test clean nopyc

build:
	./setup.py build

test:
	nosetests

cover:
	nosetests --cover-package=async_keepalive_httpc --with-cover --cover-tests --cover-html

clean: nopyc
	rm -rf ./cover
	rm -rf ./build

nopyc:
	find . -name '*.pyc' -delete