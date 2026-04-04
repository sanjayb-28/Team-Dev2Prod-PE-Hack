#!/bin/sh
set -eu

if [ -f /etc/nginx/tls/tls.crt ] && [ -f /etc/nginx/tls/tls.key ]; then
  cp /etc/nginx/templates/https.conf /etc/nginx/conf.d/default.conf
else
  cp /etc/nginx/templates/http.conf /etc/nginx/conf.d/default.conf
fi

exec nginx -g 'daemon off;'
