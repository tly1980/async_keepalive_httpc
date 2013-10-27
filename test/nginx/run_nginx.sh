#!/bin/bash
cfg=`pwd`/nginx.conf
use_https=$1
if [[ "$use_https" = '-s' ]]; then
	cfg=`pwd`/nginx_https.conf
	echo "using https"
fi

echo "config file is ${cfg} ..."
nginx -c $cfg