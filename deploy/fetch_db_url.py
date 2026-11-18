"""
Builds DATABASE_URL from the RDS-managed secret (Secrets Manager).

Run by systemd before gunicorn starts (ExecStartPre) and by the deploy script.
Writes to a tmpfs path (/run/ecommerce) so the password never touches disk.
"""
import json
import os
import pathlib
import urllib.parse

import boto3

out_dir = pathlib.Path(os.environ.get("SECRETS_DIR", "/run/ecommerce"))
out_dir.mkdir(parents=True, exist_ok=True)

client = boto3.client("secretsmanager", region_name=os.environ["AWS_S3_REGION_NAME"])
secret = json.loads(client.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])["SecretString"])

# RDS-generated passwords may contain special characters: URL-encode them
user = urllib.parse.quote(secret["username"], safe="")
password = urllib.parse.quote(secret["password"], safe="")
url = f"postgres://{user}:{password}@{os.environ['DB_HOST']}:5432/{os.environ['DB_NAME']}"

target = out_dir / "db.env"
fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
with os.fdopen(fd, "w") as f:
    f.write(f'DATABASE_URL="{url}"\n')
