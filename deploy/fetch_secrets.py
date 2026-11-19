"""Fetches runtime secrets from Secrets Manager into tmpfs.

Run by systemd before gunicorn starts (ExecStartPre) and before manage.py
commands. Writes to /run/ecommerce (memory), so nothing touches disk.
"""
import os
import json
import pathlib
import urllib.parse

import boto3

out_dir = pathlib.Path(os.environ.get("SECRETS_DIR", "/run/ecommerce"))
out_dir.mkdir(parents=True, exist_ok=True)

client = boto3.client("secretsmanager", region_name=os.environ["AWS_S3_REGION_NAME"])


def get_secret(secret_id):
    return client.get_secret_value(SecretId=secret_id)["SecretString"]


# Database: RDS-generated passwords may contain special characters, so URL-encode
db = json.loads(get_secret(os.environ["DB_SECRET_ARN"]))
user = urllib.parse.quote(db["username"], safe="")
password = urllib.parse.quote(db["password"], safe="")
database_url = f"postgres://{user}:{password}@{os.environ['DB_HOST']}:5432/{os.environ['DB_NAME']}"

# Password that encrypts the signing private key (token_urlsafe: safe inside quotes)
signing_password = get_secret(os.environ["SIGNING_KEY_SECRET_ID"])

target = out_dir / "secrets.env"
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    f.write(f'DATABASE_URL="{database_url}"\n')
    f.write(f'SIGNING_KEY_PASSWORD="{signing_password}"\n')