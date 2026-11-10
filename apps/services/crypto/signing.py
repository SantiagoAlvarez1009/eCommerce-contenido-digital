import base64
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from django.conf import settings


class SigningKeyError(Exception):
    pass


def _read_key_file(path):
    path = Path(path)
    if not path.is_file():
        raise SigningKeyError(f'No se encontro la clave en {path}. Ejecuta: python manage.py generate_signing_keys')
    return path.read_bytes()


def load_private_key():
    key = serialization.load_pem_private_key(_read_key_file(settings.SIGNING_PRIVATE_KEY_PATH), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise SigningKeyError('La clave privada no es Ed25519.')
    return key


def load_public_key():
    key = serialization.load_pem_public_key(_read_key_file(settings.SIGNING_PUBLIC_KEY_PATH))
    if not isinstance(key, Ed25519PublicKey):
        raise SigningKeyError('La clave publica no es Ed25519.')
    return key


def sign(data):
    signature = load_private_key().sign(data)
    return base64.b64encode(signature).decode('ascii')


def verify(data, signature_b64):
    try:
        signature = base64.b64decode(signature_b64.strip(), validate=True)
        load_public_key().verify(signature, data)
        return True
    except (InvalidSignature, ValueError):
        return False