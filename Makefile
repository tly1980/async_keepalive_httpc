.PHONY: build test clean

build:
	./setup.py build

test:
	nosetests

cover:
	nosetests --cover-package=async_keepalive_httpc --with-cover --cover-tests --cover-html

clean:
	rm -rf ./cover
	rm -rf ./build