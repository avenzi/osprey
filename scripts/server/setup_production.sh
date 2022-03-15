#!/usr/bin/env bash

# register certbot nginx with signalstream.org
certbot --nginx -d signalstream.org

echo "Writing Crontab line to renew SSl certification..."
webroot="$(pwd -P)/app"  # get absolute path to website root
echo ${webroot}
(crontab -l ; echo "0 12 * * * certbot renew --webroot -w ${webroot}") 2>/dev/null | sort | uniq | crontab -
