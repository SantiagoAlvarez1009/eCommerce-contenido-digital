#!/bin/bash
# Runs manage.py with production env + runtime secrets (never written to disk).
# Usage: sudo -u django bash /opt/ecommerce/app/deploy/manage.sh <command> [args]
set -euo pipefail

set -a; . /etc/ecommerce/ecommerce.env; set +a
export DJANGO_SETTINGS_MODULE=config.settings.production

SECRETS_DIR=$(mktemp -d); export SECRETS_DIR
trap 'rm -rf "$SECRETS_DIR"' EXIT

/opt/ecommerce/venv/bin/python /opt/ecommerce/app/deploy/fetch_secrets.py
set -a; . "$SECRETS_DIR/secrets.env"; set +a

cd /opt/ecommerce/app
/opt/ecommerce/venv/bin/python manage.py "$@"