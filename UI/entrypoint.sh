#!/bin/sh
set -e

# entrypoint.sh

# Set default if not provided
: "${API_BASE_URL:=http://localhost:8080}"

mkdir -p /opt/app-root/src/config

cat <<EOF > /opt/app-root/src/config/config.ts
window.APP_CONFIG = {
  API_BASE_URL: "${API_BASE_URL}"
};
EOF

# Start Nginx (or your web server)
nginx -g 'daemon off;'
