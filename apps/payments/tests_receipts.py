import shutil
import tempfile

from django.core.files.base import ContentFile
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.orders.models import Order
from apps.products.models import DigitalProduct
from apps.services.crypto import signing
from apps.users.models import User
from .models import PaymentReceipt

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class ReceiptSignatureTests(TestCase):
    PASSWORD = 'Una-Clave-Larga-98765'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.product = DigitalProduct(name='Manual', description='Manual de prueba', price='10.50')
        self.product.file_path.save('manual.txt', ContentFile(b'contenido original'), save=False)
        self.product.save()
        self.user = User.objects.create_user(email='ana@test.com', password=self.PASSWORD, name='Ana')
        self.client.force_login(self.user)

    def buy(self):
        self.client.post(reverse('cart:add', args=[self.product.pk]))
        self.client.post(reverse('orders:checkout'))
        order = Order.objects.filter(user=self.user).latest('created_at')
        self.client.post(reverse('payments:pay', args=[order.pk]), {'result': 'approved'})
        return PaymentReceipt.objects.get(payment__order=order)

    def test_approved_payment_creates_signed_receipt(self):
        receipt = self.buy()
        self.assertTrue(receipt.signature)
        self.assertTrue(signing.verify(receipt.read_bytes(), receipt.signature))

    def test_modified_receipt_fails_verification(self):
        receipt = self.buy()
        tampered = receipt.read_bytes().replace(b'$10.50', b'$1.00')
        self.assertNotEqual(tampered, receipt.read_bytes())
        self.assertFalse(signing.verify(tampered, receipt.signature))

    def test_signature_download_only_for_owner(self):
        receipt = self.buy()
        response = self.client.get(reverse('payments:receipt_signature', args=[receipt.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), receipt.signature)

        other = User.objects.create_user(email='otro@test.com', password=self.PASSWORD, name='Otro')
        self.client.force_login(other)
        response = self.client.get(reverse('payments:receipt_signature', args=[receipt.pk]))
        self.assertEqual(response.status_code, 404)

    def test_receipt_page_shows_signature(self):
        receipt = self.buy()
        response = self.client.get(reverse('payments:receipt_detail', args=[receipt.pk]))
        self.assertContains(response, receipt.signature)


    def verify(self, content, signature):
        return self.client.post(reverse('payments:receipt_verify'), {
            'receipt_file'  : SimpleUploadedFile('comprobante.txt', content),
            'signature_file': SimpleUploadedFile('comprobante.sig', signature.encode('ascii')),
        })

    def test_verify_page_accepts_original_receipt(self):
        receipt  = self.buy()
        response = self.verify(receipt.read_bytes(), receipt.signature)
        self.assertEqual(response.context['result'], True)
        self.assertContains(response, 'Firma válida')

    def test_verify_page_rejects_modified_receipt(self):
        receipt  = self.buy()
        tampered = receipt.read_bytes().replace(b'$10.50', b'$1.00')
        response = self.verify(tampered, receipt.signature)
        self.assertEqual(response.context['result'], False)
        self.assertContains(response, 'Firma inválida')

    def test_verify_page_accepts_pasted_signature(self):
        receipt  = self.buy()
        response = self.client.post(reverse('payments:receipt_verify'), {
            'receipt_file'  : SimpleUploadedFile('comprobante.txt', receipt.read_bytes()),
            'signature_text': receipt.signature,
        })
        self.assertEqual(response.context['result'], True)

    def test_verify_page_requires_signature(self):
        response = self.client.post(reverse('payments:receipt_verify'), {
            'receipt_file': SimpleUploadedFile('comprobante.txt', b'texto'),
        })
        self.assertIsNone(response.context['result'])
        self.assertContains(response, 'Sube el archivo .sig o pega la firma.')

    def test_verify_page_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('payments:receipt_verify'))
        self.assertEqual(response.status_code, 302)

    def test_public_key_can_be_downloaded(self):
        response = self.client.get(reverse('payments:public_key'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'BEGIN PUBLIC KEY', b''.join(response.streaming_content))