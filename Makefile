.PHONY: build test clean nopyc bump register upload

test:
	nosetests

test_with_proxy:
	export PROXY_HOST=http://127.0.0.1; export PROXY_PORT=8888; nosetests

register: dist
	python setup.py sdist register

cover:
	nosetests --cover-package=async_keepalive_httpc --with-cover --cover-tests --cover-html

clean: nopyc
	rm -rf *.egg-info/
	rm -rf ./cover
	rm -rf ./build
	rm -rf ./dist

nopyc:
	find . -name '*.pyc' -delete

dist:
	./setup.py sdist

upload:
	python setup.py sdist upload


bump:
	cd async_keepalive_httpc && bumpversion
