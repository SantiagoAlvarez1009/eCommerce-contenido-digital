from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from apps.orders.models import Order
from apps.users.models import User
from .models import SecurityEvent
from .services import client_ip


class ClientIpTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, **meta):
        return self.factory.get('/', **meta)

    @override_settings(SECURITY_EVENTS_TRUST_X_REAL_IP=False)
    def test_uses_remote_addr_by_default(self):
        request = self.request(REMOTE_ADDR='10.0.0.5', HTTP_X_REAL_IP='203.0.113.9')
        self.assertEqual(client_ip(request), '10.0.0.5')

    @override_settings(SECURITY_EVENTS_TRUST_X_REAL_IP=True)
    def test_uses_x_real_ip_behind_trusted_proxy(self):
        request = self.request(REMOTE_ADDR='', HTTP_X_REAL_IP='203.0.113.9')
        self.assertEqual(client_ip(request), '203.0.113.9')

    @override_settings(SECURITY_EVENTS_TRUST_X_REAL_IP=True)
    def test_invalid_x_real_ip_falls_back_to_remote_addr(self):
        request = self.request(REMOTE_ADDR='10.0.0.5', HTTP_X_REAL_IP='no-es-una-ip')
        self.assertEqual(client_ip(request), '10.0.0.5')

    def test_missing_address_is_stored_as_none(self):
        self.assertIsNone(client_ip(self.request(REMOTE_ADDR='')))


class OrderStatusEventTests(TestCase):
    PASSWORD = 'Una-Clave-Larga-98765'

    def test_status_change_is_logged(self):
        customer = User.objects.create_user(email='ana@test.com', password=self.PASSWORD, name='Ana')
        operator = User.objects.create_user(
            email='operador@test.com', password=self.PASSWORD, name='Operador', role=User.Role.OPERATOR
        )
        order = Order.objects.create(user=customer, total='10.00')
        self.client.force_login(operator)
        self.client.post(reverse('orders:manage_detail', args=[order.pk]), {'status': Order.Status.PROCESSING})
        event = SecurityEvent.objects.get(event=SecurityEvent.Event.ORDER_STATUS_CHANGED)
        self.assertEqual(event.user, operator)
        self.assertIn(f'Orden #{order.pk}', event.details)
        self.assertIn('Procesando', event.details)
