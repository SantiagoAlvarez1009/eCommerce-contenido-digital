import os
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.services.crypto.signing import key_password


class Command(BaseCommand):
    help = 'Genera el par de claves Ed25519 para firmar comprobantes.'

    def add_arguments(self, parser):
        parser.add_argument('--force', action='store_true', help='Sobrescribe claves existentes.')

    def handle(self, *args, **options):
        private_path = Path(settings.SIGNING_PRIVATE_KEY_PATH)
        public_path  = Path(settings.SIGNING_PUBLIC_KEY_PATH)

        if private_path.exists() and not options['force']:
            raise CommandError(f'Ya existe {private_path}. Usa --force para reemplazarla.')

        password   = key_password()
        encryption = serialization.BestAvailableEncryption(password) if password else serialization.NoEncryption()

        key = Ed25519PrivateKey.generate()
        private_pem = key.private_bytes(
            encoding             = serialization.Encoding.PEM,
            format               = serialization.PrivateFormat.PKCS8,
            encryption_algorithm = encryption,
        )
        public_pem = key.public_key().public_bytes(
            encoding = serialization.Encoding.PEM,
            format   = serialization.PublicFormat.SubjectPublicKeyInfo,
        )

        private_path.parent.mkdir(parents=True, exist_ok=True)
        public_path.parent.mkdir(parents=True, exist_ok=True)

        fd = os.open(private_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'wb') as f:
            f.write(private_pem)
        public_path.write_bytes(public_pem)

        protection = 'cifrada con SIGNING_KEY_PASSWORD' if password else 'SIN cifrar: define SIGNING_KEY_PASSWORD para protegerla'
        self.stdout.write(self.style.SUCCESS(f'Clave privada: {private_path} (permisos 600, {protection})'))
        self.stdout.write(self.style.SUCCESS(f'Clave publica: {public_path}'))