.PHONY: build test clean nopyc bump

test:
	nosetests

cover:
	nosetests --cover-package=async_keepalive_httpc --with-cover --cover-tests --cover-html

clean: nopyc
	rm -rf ./cover
	rm -rf ./build
	rm -rf ./dist

nopyc:
	find . -name '*.pyc' -delete

dist:
	./setup.py sdist

bump:
	cd async_keepalive_httpc && bumpversion
