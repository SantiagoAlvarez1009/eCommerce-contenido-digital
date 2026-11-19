from django.test import TestCase

from .models import User


class PasswordHashingTests(TestCase):
    PASSWORD = 'Contra-Super-Segura-007'

    def test_password_is_stored_with_argon2id(self):
        user = User.objects.create_user(email='jamesbond@test.com', password=self.PASSWORD, name='Pattinson')
        self.assertTrue(user.password.startswith('argon2$argon2id$'))
        self.assertNotIn(self.PASSWORD, user.password)
        self.assertTrue(user.check_password(self.PASSWORD))
        self.assertFalse(user.check_password('incorrecta'))

    def test_legacy_pbkdf2_hash_is_upgraded_on_login(self):
        from django.contrib.auth.hashers import make_password
        user = User.objects.create_user(email='jamesbond@test.com', password=None, name='Craig')
        user.password = make_password(self.PASSWORD, hasher='pbkdf2_sha256')
        user.save()
        self.assertTrue(self.client.login(email='jamesbond@test.com', password=self.PASSWORD))
        user.refresh_from_db()
        self.assertTrue(user.password.startswith('argon2$argon2id$'))