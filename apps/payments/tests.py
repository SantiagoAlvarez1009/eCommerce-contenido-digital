"""
Tests for simulated payments and receipts
    payment flow, receipt content, access to receipts and 
    end-to-end signature verification with the files the client downloads.
"""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls                    import reverse

from apps.orders.models          import Order
from apps.security_events.models import SecurityEvent
from apps.services.testing       import AppTestCase
from .forms                      import SimulatedPaymentForm
from .models                     import Payment, PaymentReceipt

Event = SecurityEvent.Event


class PaymentTestCase(AppTestCase):

    def setUp(self):
        self.user    = self.make_user()
        self.product = self.make_product('Manual', price='10.50')
        self.client.force_login(self.user)

    def checkout(self, product=None):
        self.client.post(reverse('cart:add', args=[(product or self.product).pk]))
        self.client.post(reverse('orders:checkout'))
        return Order.objects.filter(user=self.user).latest('created_at')

    def pay(self, order, result='approved'):
        response = self.client.post(reverse('payments:pay', args=[order.pk]), {'result': result})
        order.refresh_from_db()
        return response


class SimulatedPaymentTests(PaymentTestCase):

    def test_payment_form_collects_no_card_or_bank_data(self):
        self.assertEqual(list(SimulatedPaymentForm().fields), ['result'])
        response = self.client.get(reverse('payments:pay', args=[self.checkout().pk]))
        self.assertEqual(response.status_code, 200)
        for field in ('card', 'cvv', 'tarjeta', 'cuenta'):
            self.assertNotContains(response, f'name="{field}')

    def test_payments_table_has_no_financial_data_columns(self):
        columns = {field.name for field in Payment._meta.get_fields()}
        self.assertEqual(columns, {'id', 'order', 'amount', 'status', 'created_at', 'transaction_reference', 'receipts'})

    def test_approved_payment_completes_order_and_creates_receipt(self):
        order = self.checkout()
        self.pay(order)
        payment = order.payments.get()
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertEqual(payment.status, Payment.Status.COMPLETED)
        self.assertEqual(payment.amount, order.total)
        self.assertRegex(payment.transaction_reference, r'^SIM-[0-9A-F]{12}$')
        self.assertEqual(payment.receipts.count(), 1)

    def test_failed_payment_keeps_order_pending_without_receipt(self):
        order = self.checkout()
        self.pay(order, 'failed')
        payment = order.payments.get()
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertEqual(payment.status, Payment.Status.FAILED)
        self.assertFalse(PaymentReceipt.objects.exists())

    def test_failed_payment_can_be_retried(self):
        order = self.checkout()
        self.pay(order, 'failed')
        self.pay(order, 'approved')
        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertEqual(order.payments.count(), 2)
        self.assertEqual(PaymentReceipt.objects.count(), 1)

    def test_invalid_result_creates_no_payment(self):
        order = self.checkout()
        self.pay(order, 'gratis')
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_paid_order_cannot_be_paid_again(self):
        order = self.checkout()
        self.pay(order)
        response = self.pay(order)
        self.assertRedirects(response, reverse('orders:detail', args=[order.pk]))
        self.assertEqual(order.payments.count(), 1)

    def test_cancelled_order_cannot_be_paid(self):
        order = self.checkout()
        self.client.post(reverse('orders:cancel', args=[order.pk]))
        self.pay(order)
        self.assertEqual(order.status, Order.Status.CANCELLED)
        self.assertFalse(Payment.objects.exists())

    def test_amount_uses_price_frozen_in_the_order(self):
        order = self.checkout()
        self.product.price = Decimal('99.00')
        self.product.save()
        self.pay(order)
        self.assertEqual(order.payments.get().amount, Decimal('10.50'))
        self.assertIn('$10.50', PaymentReceipt.objects.get().read_text())

    def test_payment_requires_login(self):
        order = self.checkout()
        self.client.logout()
        self.assertRedirectsToLogin(self.client.post(reverse('payments:pay', args=[order.pk]), {'result': 'approved'}))
        self.assertFalse(Payment.objects.exists())

    def test_client_cannot_pay_another_clients_order(self):
        order = self.checkout()
        self.client.force_login(self.make_user('otro@test.com'))
        response = self.pay(order)
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Payment.objects.exists())
        self.assertEqual(order.status, Order.Status.PENDING)

    def test_approved_payment_logs_payment_and_signature_events(self):
        self.pay(self.checkout())
        self.assertTrue(SecurityEvent.objects.filter(event=Event.PAYMENT_APPROVED, user=self.user).exists())
        self.assertTrue(SecurityEvent.objects.filter(event=Event.SIGNATURE_CREATED, user=self.user).exists())

    def test_failed_payment_logs_no_approval(self):
        self.pay(self.checkout(), 'failed')
        self.assertFalse(SecurityEvent.objects.filter(event=Event.PAYMENT_APPROVED).exists())


class ReceiptContentTests(PaymentTestCase):

    def setUp(self):
        super().setUp()
        self.guia  = self.make_product('Guia', price='4.50')
        self.client.post(reverse('cart:add', args=[self.guia.pk]))
        self.order = self.checkout()
        self.pay(self.order)
        self.payment = self.order.payments.get()
        self.text    = PaymentReceipt.objects.get().read_text()

    def test_receipt_includes_required_fields(self):
        # Order number, user, products, total, date and transaction reference.
        self.assertIn(f'Orden        : {self.order.pk}', self.text)
        self.assertIn(self.user.email, self.text)
        self.assertIn('Manual  $10.50', self.text)
        self.assertIn('Guia  $4.50', self.text)
        self.assertIn('Total        : $15.00', self.text)
        self.assertIn(f'{self.payment.created_at:%Y-%m-%d}', self.text)
        self.assertIn(self.payment.transaction_reference, self.text)


class ReceiptAccessTests(PaymentTestCase):

    def setUp(self):
        super().setUp()
        self.pay(self.checkout())
        self.receipt = PaymentReceipt.objects.get()

    def receipt_urls(self):
        return [
            reverse('payments:receipt_detail'   , args=[self.receipt.pk]),
            reverse('payments:receipt_download' , args=[self.receipt.pk]),
            reverse('payments:receipt_signature', args=[self.receipt.pk]),
        ]

    def test_owner_can_open_list_detail_and_downloads(self):
        self.assertContains(self.client.get(reverse('payments:receipts')), f'#{self.receipt.payment.order_id}')
        for url in self.receipt_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_other_client_cannot_access_the_receipt(self):
        self.client.force_login(self.make_user('otro@test.com'))
        self.assertNotContains(self.client.get(reverse('payments:receipts')), self.user.email)
        for url in self.receipt_urls():
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_anonymous_is_sent_to_login(self):
        self.client.logout()
        for url in self.receipt_urls() + [reverse('payments:receipts')]:
            with self.subTest(url=url):
                self.assertRedirectsToLogin(self.client.get(url))

    def test_public_key_is_public(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('payments:public_key')).status_code, 200)


class ReceiptVerificationFlowTests(PaymentTestCase):
    """Client flow: download the receipt and its .sig, then verify them on the site."""

    def setUp(self):
        super().setUp()
        self.pay(self.checkout())
        self.receipt = PaymentReceipt.objects.get()

    def download_receipt(self, receipt=None):
        receipt  = receipt or self.receipt
        response = self.client.get(reverse('payments:receipt_download', args=[receipt.pk]))
        content  = b''.join(response.streaming_content)
        signature = self.client.get(reverse('payments:receipt_signature', args=[receipt.pk])).content
        return content, signature

    def verify(self, content, signature):
        response = self.client.post(reverse('payments:receipt_verify'), {
            'receipt_file'  : SimpleUploadedFile('comprobante.txt', content),
            'signature_file': SimpleUploadedFile('comprobante.sig', signature),
        })
        return response.context['result']

    def test_downloaded_receipt_is_identical_to_the_signed_one(self):
        content, signature = self.download_receipt()
        self.assertEqual(content, self.receipt.read_bytes())
        self.assertEqual(signature.decode(), self.receipt.signature)

    def test_downloaded_original_receipt_is_valid(self):
        self.assertIs(self.verify(*self.download_receipt()), True)

    def test_downloaded_receipt_modified_is_invalid(self):
        content, signature = self.download_receipt()
        tampered = {
            'total'     : content.replace(b'$10.50', b'$0.50'),
            'one byte'  : content[:-1] + bytes([content[-1] ^ 1]),
            'extra line': content + b'\nProducto extra  $0.00',
        }
        for case, data in tampered.items():
            with self.subTest(case=case):
                self.assertIs(self.verify(data, signature), False)

    def test_signature_of_another_receipt_is_invalid(self):
        other_product = self.make_product('Guia', price='4.50')
        self.pay(self.checkout(other_product))
        other = PaymentReceipt.objects.exclude(pk=self.receipt.pk).get()

        content, _         = self.download_receipt()
        _, other_signature = self.download_receipt(other)
        self.assertIs(self.verify(content, other_signature), False)

    def test_malformed_signature_is_invalid_without_error(self):
        content, _ = self.download_receipt()
        for signature in (b'no-es-base64!!', b'QUJD', b' '):
            with self.subTest(signature=signature):
                response = self.client.post(reverse('payments:receipt_verify'), {
                    'receipt_file'  : SimpleUploadedFile('comprobante.txt', content),
                    'signature_text': signature.decode(),
                })
                self.assertEqual(response.status_code, 200)
                self.assertIn(response.context['result'], (False, None))