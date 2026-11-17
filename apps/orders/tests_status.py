from django.test import TestCase
from django.urls import reverse

from apps.users.models import User
from .forms import OrderStatusForm
from .models import Order
from .services import InvalidStatusTransition, change_order_status


class OrderStatusTests(TestCase):
    PASSWORD = 'Una-Clave-Larga-98765'

    def setUp(self):
        self.client_user = User.objects.create_user(email='ana@test.com', password=self.PASSWORD, name='Ana')
        self.operator = User.objects.create_user(
            email='operador@test.com', password=self.PASSWORD, name='Operador', role=User.Role.OPERATOR
        )
        self.client.force_login(self.operator)

    def order(self, status):
        return Order.objects.create(user=self.client_user, total='10.00', status=status)

    def change(self, order, status):
        response = self.client.post(reverse('orders:manage_detail', args=[order.pk]), {'status': status})
        order.refresh_from_db()
        return response

    def test_operator_moves_pending_order_to_processing(self):
        order = self.order(Order.Status.PENDING)
        self.change(order, Order.Status.PROCESSING)
        self.assertEqual(order.status, Order.Status.PROCESSING)

    def test_operator_cancels_pending_order(self):
        order = self.order(Order.Status.PENDING)
        self.change(order, Order.Status.CANCELLED)
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_operator_cannot_mark_order_as_completed(self):
        order = self.order(Order.Status.PENDING)
        self.change(order, Order.Status.COMPLETED)
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_completed_order_cannot_be_reverted(self):
        order = self.order(Order.Status.COMPLETED)
        for status in (Order.Status.PENDING, Order.Status.PROCESSING, Order.Status.CANCELLED):
            self.change(order, status)
            self.assertEqual(order.status, Order.Status.COMPLETED)

    def test_cancelled_order_cannot_be_reopened(self):
        order = self.order(Order.Status.CANCELLED)
        self.change(order, Order.Status.PENDING)
        self.assertEqual(order.status, Order.Status.CANCELLED)

    def test_completed_order_page_shows_final_state_without_form(self):
        order = self.order(Order.Status.COMPLETED)
        response = self.client.get(reverse('orders:manage_detail', args=[order.pk]))
        self.assertContains(response, 'estado final')
        self.assertNotContains(response, 'Actualizar estado')

    def test_form_only_offers_allowed_transitions(self):
        form = OrderStatusForm(order=self.order(Order.Status.PENDING))
        values = [value for value, label in form.fields['status'].choices]
        self.assertEqual(values, [Order.Status.PROCESSING, Order.Status.CANCELLED])

    def test_service_rejects_invalid_transition(self):
        order = self.order(Order.Status.COMPLETED)
        with self.assertRaises(InvalidStatusTransition):
            change_order_status(order, Order.Status.PENDING)

    def test_client_cannot_change_order_status(self):
        order = self.order(Order.Status.PENDING)
        self.client.force_login(self.client_user)
        response = self.change(order, Order.Status.CANCELLED)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(order.status, Order.Status.PENDING)
