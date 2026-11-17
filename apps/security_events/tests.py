import shutil
import tempfile

from django.contrib.auth.tokens import default_token_generator
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.orders.models import Order
from apps.products.models import DigitalProduct
from apps.users.models import User
from .models import SecurityEvent
from .services import log_event

MEDIA = tempfile.mkdtemp()
Event  = SecurityEvent.Event
Result = SecurityEvent.Result


@override_settings(MEDIA_ROOT=MEDIA)
class SecurityEventTests(TestCase):
    PASSWORD = 'Una-Clave-Larga-98765'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.client_user = User.objects.create_user(email='ana@test.com', password=self.PASSWORD, name='Ana')
        self.admin = User.objects.create_user(
            email='admin@test.com', password=self.PASSWORD, name='Admin', role=User.Role.ADMIN
        )
        self.operator = User.objects.create_user(
            email='operador@test.com', password=self.PASSWORD, name='Operador', role=User.Role.OPERATOR
        )
        self.product = DigitalProduct(name='Manual', description='Manual de prueba', price='10.00')
        self.product.file_path.save('manual.txt', ContentFile(b'contenido original'), save=False)
        self.product.save()

    def last(self, event):
        return SecurityEvent.objects.filter(event=event).latest('created_at')

    def buy(self):
        self.client.post(reverse('cart:add', args=[self.product.pk]))
        self.client.post(reverse('orders:checkout'))
        order = Order.objects.filter(user=self.client_user).latest('created_at')
        self.client.post(reverse('payments:pay', args=[order.pk]), {'result': 'approved'})
        return order

    def test_login_success_is_logged_with_origin(self):
        self.client.post(reverse('users:login'), {'username': 'ana@test.com', 'password': self.PASSWORD})
        event = self.last(Event.LOGIN_SUCCESS)
        self.assertEqual(event.user, self.client_user)
        self.assertEqual(event.result, Result.SUCCESS)
        self.assertEqual(event.origin, '127.0.0.1')

    def test_login_failed_is_logged_without_password(self):
        self.client.post(reverse('users:login'), {'username': 'ana@test.com', 'password': 'incorrecta'})
        event = self.last(Event.LOGIN_FAILED)
        self.assertEqual(event.email, 'ana@test.com')
        self.assertEqual(event.result, Result.FAILURE)
        self.assertIsNone(event.user)
        self.assertNotIn('incorrecta', event.details)

    def test_logout_is_logged(self):
        self.client.force_login(self.client_user)
        self.client.post(reverse('users:logout'))
        self.assertEqual(self.last(Event.LOGOUT).user, self.client_user)

    def test_purchase_logs_order_payment_and_signature(self):
        self.client.force_login(self.client_user)
        order = self.buy()
        self.assertIn(f'#{order.pk}', self.last(Event.ORDER_CREATED).details)
        self.assertIn(f'#{order.pk}', self.last(Event.PAYMENT_APPROVED).details)
        self.assertIn(f'#{order.pk}', self.last(Event.SIGNATURE_CREATED).details)

    def test_download_logs_fingerprint_once_and_each_download(self):
        self.client.force_login(self.client_user)
        self.buy()
        self.client.get(reverse('downloads:download', args=[self.product.pk]))
        self.client.get(reverse('downloads:download', args=[self.product.pk]))
        self.assertEqual(SecurityEvent.objects.filter(event=Event.FINGERPRINT_CREATED).count(), 1)
        self.assertEqual(
            SecurityEvent.objects.filter(event=Event.DOWNLOAD, result=Result.SUCCESS).count(), 2
        )

    def test_denied_download_is_logged_as_failure(self):
        self.client.force_login(self.client_user)
        self.client.get(reverse('downloads:download', args=[self.product.pk]))
        event = self.last(Event.DOWNLOAD)
        self.assertEqual(event.result, Result.FAILURE)
        self.assertFalse(SecurityEvent.objects.filter(event=Event.FINGERPRINT_CREATED).exists())

    def test_role_change_is_logged(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('users:manage_role', args=[self.client_user.pk]), {'role': User.Role.OPERATOR})
        event = self.last(Event.ROLE_CHANGED)
        self.assertEqual(event.user, self.admin)
        self.assertIn('ana@test.com', event.details)

    def test_account_disabled_and_enabled_are_logged(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('users:manage_toggle', args=[self.client_user.pk]))
        self.assertIn('ana@test.com', self.last(Event.ACCOUNT_DISABLED).details)
        self.client.post(reverse('users:manage_toggle', args=[self.client_user.pk]))
        self.assertIn('ana@test.com', self.last(Event.ACCOUNT_ENABLED).details)

    def test_session_revocation_is_logged(self):
        self.client.force_login(self.admin)
        self.client.post(reverse('users:manage_revoke', args=[self.client_user.pk]))
        self.assertIn('ana@test.com', self.last(Event.SESSION_REVOKED).details)

    def test_password_reset_is_logged(self):
        uid   = urlsafe_base64_encode(force_bytes(self.client_user.pk))
        token = default_token_generator.make_token(self.client_user)
        response = self.client.get(reverse('users:password_reset_confirm', args=[uid, token]))
        new_password = 'Otra-Clave-Larga-12345'
        self.client.post(response.url, {'new_password1': new_password, 'new_password2': new_password})
        self.assertEqual(self.last(Event.PASSWORD_RESET).user, self.client_user)

    def test_admin_can_list_events(self):
        log_event(Event.LOGIN_FAILED, result=Result.FAILURE, email='intruso@test.com')
        self.client.force_login(self.admin)
        response = self.client.get(reverse('security_events:list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'intruso@test.com')

    def test_admin_can_filter_events(self):
        log_event(Event.LOGIN_FAILED, result=Result.FAILURE, email='intruso@test.com')
        log_event(Event.ORDER_CREATED, user=self.client_user, details='Orden #99')
        self.client.force_login(self.admin)
        response = self.client.get(reverse('security_events:list'), {'evento': Event.LOGIN_FAILED})
        self.assertContains(response, 'intruso@test.com')
        self.assertNotContains(response, 'Orden #99')

    def test_operator_and_client_cannot_list_events(self):
        for user in (self.operator, self.client_user):
            self.client.force_login(user)
            response = self.client.get(reverse('security_events:list'))
            self.assertEqual(response.status_code, 403)

    def test_events_cannot_be_modified_or_deleted(self):
        event = log_event(Event.LOGIN_FAILED, result=Result.FAILURE, email='intruso@test.com')
        event.details = 'alterado'
        with self.assertRaises(ValueError):
            event.save()
        with self.assertRaises(ValueError):
            event.delete()
        self.assertTrue(SecurityEvent.objects.filter(pk=event.pk, details='').exists())
