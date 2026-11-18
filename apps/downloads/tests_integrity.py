import io
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.orders.models import Order
from apps.products.models import DigitalProduct
from apps.security_events.models import SecurityEvent
from apps.users.models import User
from .models import FingerPrint

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class ProductIntegrityTests(TestCase):
    PASSWORD = 'Una-Clave-Larga-98765'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.product = DigitalProduct(name='Manual', description='Manual de prueba', price='10.00')
        self.product.file_path.save('manual.txt', ContentFile(b'contenido original'), save=False)
        self.product.save()
        self.user = User.objects.create_user(email='ana@test.com', password=self.PASSWORD, name='Ana')
        self.client.force_login(self.user)

    def tamper(self):
        with open(self.product.file_path.path, 'wb') as f:
            f.write(b'contenido alterado')

    def buy(self):
        self.client.post(reverse('cart:add', args=[self.product.pk]))
        self.client.post(reverse('orders:checkout'))
        order = Order.objects.filter(user=self.user).latest('created_at')
        self.client.post(reverse('payments:pay', args=[order.pk]), {'result': 'approved'})

    def test_original_file_matches_expected_hash(self):
        self.assertTrue(self.product.file_is_intact())

    def test_modified_file_has_different_hash(self):
        original = self.product.file_hash
        self.tamper()
        self.assertNotEqual(self.product.current_file_hash(), original)
        self.assertFalse(self.product.file_is_intact())

    def test_tampered_product_cannot_be_downloaded(self):
        self.buy()
        self.tamper()
        response = self.client.get(reverse('downloads:download', args=[self.product.pk]))
        self.assertRedirects(response, reverse('downloads:library'))
        self.assertFalse(FingerPrint.objects.exists())
        event = SecurityEvent.objects.filter(event=SecurityEvent.Event.DOWNLOAD).latest('created_at')
        self.assertEqual(event.result, SecurityEvent.Result.FAILURE)
        self.assertIn('Integridad', event.details)

    def test_verify_command_reports_intact_products(self):
        out = io.StringIO()
        call_command('verify_product_hashes', stdout=out)
        self.assertIn('OK        Manual', out.getvalue())

    def test_verify_command_detects_tampered_product(self):
        self.tamper()
        out = io.StringIO()
        with self.assertRaises(CommandError):
            call_command('verify_product_hashes', stdout=out)
        self.assertIn('ALTERADO  Manual', out.getvalue())
