"""
Production settings for AWS.
- EC2 accesses S3 via IAM role (instance profile): do not define
  AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY; boto3 obtains temporary credentials.
- RDS (PostgreSQL) is configured with DATABASE_URL, inside the VPC.
"""

from .base import *  # noqa: F403
from .base import DATABASES, env

DEBUG = False

# RDS Database

DATABASES['default']['CONN_MAX_AGE'] = env.int('DB_CONN_MAX_AGE', default=60)
DATABASES['default'].setdefault('OPTIONS', {})['sslmode'] = env('DB_SSLMODE', default='require')


# S3: static and media

AWS_STORAGE_BUCKET_NAME = env('AWS_STORAGE_BUCKET_NAME')
AWS_S3_REGION_NAME = env('AWS_S3_REGION_NAME', default='us-east-1')
AWS_DEFAULT_ACL = None  # Bucket with ACLs disabled
AWS_S3_FILE_OVERWRITE = False
AWS_QUERYSTRING_EXPIRE = 3600  # Signed URLs for media (1 h)

STORAGES = {
    # Private media files served with signed URLs
    'default': {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': {'location': 'media'},
    },
    # Static: collectstatic uploads to S3
    'staticfiles': {
        'BACKEND': 'storages.backends.s3.S3StaticStorage',
        'OPTIONS': {'location': 'static'},
    },
}

_s3_domain = f'{AWS_STORAGE_BUCKET_NAME}.s3.{AWS_S3_REGION_NAME}.amazonaws.com'
STATIC_URL = f'https://{_s3_domain}/static/'
MEDIA_URL = f'https://{_s3_domain}/media/'


# Email (SMTP, p. eg. Amazon SES)

MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.smtp.EmailBackend',
        'OPTIONS': {
            'host': env('EMAIL_HOST', default='email-smtp.us-east-1.amazonaws.com'),
            'port': env.int('EMAIL_PORT', default=587),
            'username': env('EMAIL_HOST_USER', default=''),
            'password': env('EMAIL_HOST_PASSWORD', default=''),
            'use_tls': True,
        },
    },
}


# Security (behind ALB/nginx with TLS)

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_SSL_REDIRECT = env.bool('DJANGO_SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = env.list('DJANGO_CSRF_TRUSTED_ORIGINS', default=[])
SECURE_HSTS_SECONDS = env.int('DJANGO_SECURE_HSTS_SECONDS', default=0) # Upload to S3 and test HTTPS first


# Logging to stdout (journald in EC2)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': env('DJANGO_LOG_LEVEL', default='INFO')},
}
