"""
Tests for the users module
    password storage, registration, login/logout,
    profile, password recovery and administration of users by role.
"""
import re

from django.contrib.auth.hashers import make_password
from django.core import mail
from django.db import connection
from django.test import Client
from django.urls import reverse

from apps.cart.models import Cart
from apps.services.testing import PASSWORD, AppTestCase
from .models import User

Role = User.Role


class PasswordStorageTests(AppTestCase):

    def test_password_is_stored_with_argon2id(self):
        user = self.make_user()
        self.assertTrue(user.password.startswith('argon2$argon2id$'))
        self.assertNotIn(PASSWORD, user.password)

    def test_password_is_verified_with_the_library(self):
        user = self.make_user()
        self.assertTrue(user.check_password(PASSWORD))
        self.assertFalse(user.check_password('incorrecta'))

    def test_same_password_produces_different_hashes(self):
        # The library generates a random salt for each hash.
        first  = self.make_user('a@test.com')
        second = self.make_user('b@test.com')
        self.assertNotEqual(first.password, second.password)

    def test_legacy_pbkdf2_hash_is_upgraded_on_login(self):
        user = self.make_user()
        user.password = make_password(PASSWORD, hasher='pbkdf2_sha256')
        user.save()
        self.assertTrue(self.client.login(email=user.email, password=PASSWORD))
        user.refresh_from_db()
        self.assertTrue(user.password.startswith('argon2$argon2id$'))

    def test_users_table_has_no_plain_password_column(self):
        with connection.cursor() as cursor:
            columns = [c.name for c in connection.introspection.get_table_description(cursor, User._meta.db_table)]
        self.assertIn('password_hash', columns)
        self.assertNotIn('password', columns)


class RegistrationTests(AppTestCase):

    def register(self, email='nuevo@test.com', **extra):
        return self.client.post(reverse('users:register'), {
            'email'    : email,
            'name'     : 'Nuevo',
            'password1': PASSWORD,
            'password2': PASSWORD,
            **extra,
        })

    def test_register_creates_client_with_cart_and_logs_in(self):
        response = self.register()
        self.assertRedirects(response, reverse('catalog:list'))
        user = User.objects.get(email='nuevo@test.com')
        self.assertEqual(user.role, Role.CLIENT)
        self.assertEqual(user.status, User.Status.ACTIVE)
        self.assertTrue(Cart.objects.filter(user=user).exists())
        self.assertTrue(self.is_logged_in())

    def test_register_cannot_choose_a_role(self):
        self.register(role=Role.ADMIN)
        self.assertEqual(User.objects.get(email='nuevo@test.com').role, Role.CLIENT)

    def test_duplicate_email_is_rejected_case_insensitive(self):
        self.make_user('nuevo@test.com')
        response = self.register(email='NUEVO@test.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una cuenta con este correo.')
        self.assertEqual(User.objects.filter(email__iexact='nuevo@test.com').count(), 1)

    def test_weak_password_is_rejected(self):
        response = self.client.post(reverse('users:register'), {
            'email': 'nuevo@test.com', 'name': 'Nuevo', 'password1': '12345', 'password2': '12345',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='nuevo@test.com').exists())

    def test_email_is_stored_in_lowercase(self):
        user = User.objects.create_user(email='Mixto@Test.com', password=PASSWORD, name='Mixto')
        self.assertEqual(user.email, 'mixto@test.com')


class LoginTests(AppTestCase):

    def setUp(self):
        self.user = self.make_user()

    def login(self, password=PASSWORD, email=None):
        return self.client.post(reverse('users:login'), {
            'username': email or self.user.email,
            'password': password,
        })

    def test_correct_password_is_accepted(self):
        response = self.login()
        self.assertRedirects(response, reverse('catalog:list'))
        self.assertTrue(self.is_logged_in())

    def test_wrong_password_is_rejected(self):
        response = self.login(password='incorrecta')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.is_logged_in())

    def test_unknown_email_is_rejected(self):
        self.login(email='nadie@test.com')
        self.assertFalse(self.is_logged_in())

    def test_disabled_account_cannot_log_in(self):
        self.user.set_enabled(False)
        self.login()
        self.assertFalse(self.is_logged_in())

    def test_logout_ends_the_session(self):
        self.client.force_login(self.user)
        self.client.post(reverse('users:logout'))
        self.assertFalse(self.is_logged_in())


class ProfileTests(AppTestCase):

    def setUp(self):
        self.user = self.make_user()
        self.client.force_login(self.user)

    def test_profile_requires_login(self):
        self.client.logout()
        self.assertRedirectsToLogin(self.client.get(reverse('users:profile')))

    def test_client_updates_own_profile(self):
        self.client.post(reverse('users:profile'), {'name': 'Nombre Nuevo', 'email': self.user.email})
        self.user.refresh_from_db()
        self.assertEqual(self.user.name, 'Nombre Nuevo')

    def test_profile_cannot_change_role_or_status(self):
        self.client.post(reverse('users:profile'), {
            'name': 'Ana', 'email': self.user.email, 'role': Role.ADMIN, 'status': User.Status.INACTIVE,
        })
        self.user.refresh_from_db()
        self.assertEqual(self.user.role, Role.CLIENT)
        self.assertEqual(self.user.status, User.Status.ACTIVE)

    def test_profile_cannot_take_another_users_email(self):
        self.make_user('otro@test.com')
        response = self.client.post(reverse('users:profile'), {'name': 'Ana', 'email': 'otro@test.com'})
        self.assertContains(response, 'Ya existe una cuenta con este correo.')


class PasswordResetTests(AppTestCase):

    NEW_PASSWORD = 'Otra-Contra-Secreta-67'

    def setUp(self):
        self.user = self.make_user()

    def request_reset(self, email=None):
        return self.client.post(reverse('users:password_reset'), {'email': email or self.user.email})

    def reset_link(self):
        return re.search(r'https?://[^/]+(/\S+)', mail.outbox[-1].body).group(1)

    def set_new_password(self, link):
        response = self.client.get(link, follow=True)
        self.client.post(response.redirect_chain[-1][0], {
            'new_password1': self.NEW_PASSWORD,
            'new_password2': self.NEW_PASSWORD,
        })

    def test_reset_sends_link_and_never_the_password(self):
        self.request_reset()
        self.assertEqual(len(mail.outbox), 1)
        self.assertNotIn(PASSWORD, mail.outbox[0].body)
        self.assertIn('/cuentas/recuperar/', mail.outbox[0].body)

    def test_unknown_email_gets_same_response_but_no_email(self):
        response = self.request_reset(email='nadie@test.com')
        self.assertRedirects(response, reverse('users:password_reset_done'))
        self.assertEqual(len(mail.outbox), 0)

    def test_new_password_replaces_old_one_with_new_hash(self):
        old_hash = self.user.password
        self.request_reset()
        self.set_new_password(self.reset_link())
        self.user.refresh_from_db()
        self.assertNotEqual(self.user.password, old_hash)
        self.assertTrue(self.user.password.startswith('argon2$argon2id$'))
        self.assertTrue(self.user.check_password(self.NEW_PASSWORD))
        self.assertFalse(self.user.check_password(PASSWORD))

    def test_token_is_single_use(self):
        self.request_reset()
        link = self.reset_link()
        self.set_new_password(link)
        again = self.client.get(link, follow=True)
        self.assertFalse(again.context['validlink'])

    def test_invalid_token_is_rejected(self):
        self.request_reset()
        link     = re.sub(r'/[^/]+/$', '/token-invalido/', self.reset_link())
        response = self.client.get(link, follow=True)
        self.assertFalse(response.context['validlink'])


class RoleAccessTests(AppTestCase):
    """Least privilege on the user administration functions (ADMIN only)."""

    def setUp(self):
        self.make_users_for_every_role()
        self.target = self.make_user('objetivo@test.com')

    def admin_actions(self):
        return [
            ('get' , reverse('users:manage_list')                       , {}),
            ('post', reverse('users:manage_role'  , args=[self.target.pk]), {'role': Role.ADMIN}),
            ('post', reverse('users:manage_toggle', args=[self.target.pk]), {}),
            ('post', reverse('users:manage_revoke', args=[self.target.pk]), {}),
        ]

    def assert_target_unchanged(self):
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, Role.CLIENT)
        self.assertTrue(self.target.is_active)

    def test_anonymous_is_sent_to_login(self):
        for method, url, data in self.admin_actions():
            with self.subTest(url=url):
                self.assertRedirectsToLogin(getattr(self.client, method)(url, data))
        self.assert_target_unchanged()

    def test_client_cannot_use_admin_functions(self):
        self.client.force_login(self.customer)
        for method, url, data in self.admin_actions():
            with self.subTest(url=url):
                self.assertForbidden(getattr(self.client, method)(url, data))
        self.assert_target_unchanged()

    def test_operator_cannot_change_roles(self):
        self.client.force_login(self.operator)
        response = self.client.post(reverse('users:manage_role', args=[self.target.pk]), {'role': Role.ADMIN})
        self.assertForbidden(response)
        self.assert_target_unchanged()

    def test_operator_cannot_promote_itself(self):
        self.client.force_login(self.operator)
        self.client.post(reverse('users:manage_role', args=[self.operator.pk]), {'role': Role.ADMIN})
        self.operator.refresh_from_db()
        self.assertEqual(self.operator.role, Role.OPERATOR)

    def test_operator_cannot_use_other_admin_functions(self):
        self.client.force_login(self.operator)
        for method, url, data in self.admin_actions():
            with self.subTest(url=url):
                self.assertForbidden(getattr(self.client, method)(url, data))
        self.assert_target_unchanged()

    def test_admin_can_change_roles(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('users:manage_role', args=[self.target.pk]), {'role': Role.OPERATOR})
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, Role.OPERATOR)

    def test_admin_actions_require_post(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('users:manage_toggle', args=[self.target.pk]))
        self.assertEqual(response.status_code, 405)
        self.assert_target_unchanged()


class UserAdministrationTests(AppTestCase):

    def setUp(self):
        self.admin  = self.make_user('admin@test.com', Role.ADMIN)
        self.target = self.make_user('objetivo@test.com')
        self.client.force_login(self.admin)

    def test_admin_lists_users_without_exposing_password_hashes(self):
        response = self.client.get(reverse('users:manage_list'))
        self.assertContains(response, self.target.email)
        self.assertNotContains(response, self.target.password)
        self.assertNotContains(response, 'argon2')

    def test_invalid_role_is_rejected(self):
        self.client.post(reverse('users:manage_role', args=[self.target.pk]), {'role': 'superusuario'})
        self.target.refresh_from_db()
        self.assertEqual(self.target.role, Role.CLIENT)

    def test_admin_cannot_change_own_role(self):
        self.client.post(reverse('users:manage_role', args=[self.admin.pk]), {'role': Role.CLIENT})
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.role, Role.ADMIN)

    def test_admin_disables_and_enables_account(self):
        url = reverse('users:manage_toggle', args=[self.target.pk])
        self.client.post(url)
        self.target.refresh_from_db()
        self.assertFalse(self.target.is_active)
        self.assertEqual(self.target.status, User.Status.INACTIVE)

        self.client.post(url)
        self.target.refresh_from_db()
        self.assertTrue(self.target.is_active)
        self.assertEqual(self.target.status, User.Status.ACTIVE)

    def test_admin_cannot_disable_own_account(self):
        self.client.post(reverse('users:manage_toggle', args=[self.admin.pk]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)

    def test_disabling_account_ends_its_open_session(self):
        target_client = Client()
        target_client.force_login(self.target)
        self.client.post(reverse('users:manage_toggle', args=[self.target.pk]))
        self.assertRedirectsToLogin(target_client.get(reverse('users:profile')))

    def test_revoke_closes_the_users_sessions(self):
        target_client = Client()
        target_client.force_login(self.target)
        self.assertEqual(target_client.get(reverse('users:profile')).status_code, 200)

        self.client.post(reverse('users:manage_revoke', args=[self.target.pk]))
        self.assertRedirectsToLogin(target_client.get(reverse('users:profile')))
        # The admin's own session is not affected.
        self.assertEqual(self.client.get(reverse('users:manage_list')).status_code, 200)