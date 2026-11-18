import io
import tempfile
from pathlib import Path

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.services.crypto import signing

RECEIPT = (
    'COMPROBANTE DE COMPRA\n'
    'Orden        : 1\n'
    'Usuario      : cliente@demo.test\n'
    'Total        : $24.50\n'
).encode('utf-8')


class SigningTests(TestCase):
    def setUp(self):
        tmp = Path(tempfile.mkdtemp())
        self.override = override_settings(
            SIGNING_PRIVATE_KEY_PATH = tmp / 'private' / 'signing_key.pem',
            SIGNING_PUBLIC_KEY_PATH  = tmp / 'public' / 'signing_key.pub.pem',
        )
        self.override.enable()
        call_command('generate_signing_keys', stdout=io.StringIO())

    def tearDown(self):
        self.override.disable()

    def test_original_receipt_has_valid_signature(self):
        signature = signing.sign(RECEIPT)
        self.assertTrue(signing.verify(RECEIPT, signature))

    def test_modified_receipt_has_invalid_signature(self):
        signature = signing.sign(RECEIPT)
        tampered  = RECEIPT.replace(b'$24.50', b'$1.00')
        self.assertFalse(signing.verify(tampered, signature))

    def test_invalid_signature_text_is_rejected(self):
        self.assertFalse(signing.verify(RECEIPT, 'esto-no-es-base64!!'))

class EncryptedKeyTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.paths = dict(
            SIGNING_PRIVATE_KEY_PATH = self.tmp / 'private' / 'signing_key.pem',
            SIGNING_PUBLIC_KEY_PATH  = self.tmp / 'public' / 'signing_key.pub.pem',
        )

    def generate(self, password):
        with override_settings(SIGNING_KEY_PASSWORD=password, **self.paths):
            call_command('generate_signing_keys', '--force', stdout=io.StringIO())

    def test_private_key_is_encrypted_when_password_is_set(self):
        self.generate('una-contrasena-larga')
        content = self.paths['SIGNING_PRIVATE_KEY_PATH'].read_bytes()
        self.assertIn(b'ENCRYPTED PRIVATE KEY', content)

    def test_encrypted_key_signs_and_verifies_with_password(self):
        self.generate('una-contrasena-larga')
        with override_settings(SIGNING_KEY_PASSWORD='una-contrasena-larga', **self.paths):
            signature = signing.sign(RECEIPT)
            self.assertTrue(signing.verify(RECEIPT, signature))

    def test_encrypted_key_cannot_be_used_with_wrong_password(self):
        self.generate('una-contrasena-larga')
        with override_settings(SIGNING_KEY_PASSWORD='otra-contrasena', **self.paths):
            with self.assertRaises(signing.SigningKeyError):
                signing.sign(RECEIPT)

    def test_encrypted_key_cannot_be_used_without_password(self):
        self.generate('una-contrasena-larga')
        with override_settings(SIGNING_KEY_PASSWORD='', **self.paths):
            with self.assertRaises(signing.SigningKeyError):
                signing.sign(RECEIPT)
