import io
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from apps.orders.models import Order
from apps.products.models import DigitalProduct
from apps.users.models import User
from .models import Download, FingerPrint
from .services import identify_content

MEDIA = tempfile.mkdtemp()

TEXT_CONTENT = b'Manual de prueba\n\nContenido original del manual.\n'
ZERO_WIDTH = ('\u200b', '\u200c', '\u200d')


def png_bytes():
    buffer = io.BytesIO()
    Image.new('RGB', (64, 64), (200, 120, 40)).save(buffer, format='PNG')
    return buffer.getvalue()


def strip_zero_width(text):
    for char in ZERO_WIDTH:
        text = text.replace(char, '')
    return text


@override_settings(MEDIA_ROOT=MEDIA)
class DownloadTests(TestCase):
    PASSWORD = 'Una-Clave-Larga-98765'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.text_product = self.create_product('Manual', 'manual.txt', TEXT_CONTENT)
        self.image_product = self.create_product('Imagen', 'imagen.png', png_bytes())
        self.user = User.objects.create_user(email='ana@test.com', password=self.PASSWORD, name='Ana')
        self.client.force_login(self.user)

    def create_product(self, name, file_name, content):
        product = DigitalProduct(name=name, description=f'{name} de prueba', price='10.00')
        product.file_path.save(file_name, ContentFile(content), save=False)
        product.save()
        return product

    def buy(self, product, approve=True):
        self.client.post(reverse('cart:add', args=[product.pk]))
        self.client.post(reverse('orders:checkout'))
        order = Order.objects.filter(user=self.user).latest('created_at')
        self.client.post(reverse('payments:pay', args=[order.pk]), {'result': 'approved' if approve else 'failed'})
        order.refresh_from_db()
        return order

    def download(self, product):
        response = self.client.get(reverse('downloads:download', args=[product.pk]))
        self.assertEqual(response.status_code, 200)
        return b''.join(response.streaming_content)

    def test_download_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('downloads:download', args=[self.text_product.pk]))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url)

    def test_client_cannot_download_product_not_purchased(self):
        response = self.client.get(reverse('downloads:download', args=[self.text_product.pk]))
        self.assertRedirects(response, reverse('downloads:library'))
        self.assertFalse(FingerPrint.objects.exists())
        self.assertFalse(Download.objects.exists())

    def test_client_cannot_download_with_failed_payment(self):
        self.buy(self.text_product, approve=False)
        response = self.client.get(reverse('downloads:download', args=[self.text_product.pk]))
        self.assertRedirects(response, reverse('downloads:library'))
        self.assertFalse(FingerPrint.objects.exists())

    def test_client_cannot_download_product_bought_by_other_user(self):
        self.buy(self.text_product)
        other = User.objects.create_user(email='otro@test.com', password=self.PASSWORD, name='Otro')
        self.client.force_login(other)
        response = self.client.get(reverse('downloads:download', args=[self.text_product.pk]))
        self.assertRedirects(response, reverse('downloads:library'))

    def test_text_fingerprint_is_recoverable(self):
        order   = self.buy(self.text_product)
        content = self.download(self.text_product)
        found   = identify_content(content)
        self.assertIsNotNone(found)
        self.assertEqual((found.user, found.order, found.product), (self.user, order, self.text_product))

    def test_text_fingerprint_is_invisible(self):
        self.buy(self.text_product)
        content = self.download(self.text_product)
        self.assertNotEqual(content, TEXT_CONTENT)
        self.assertEqual(strip_zero_width(content.decode('utf-8')), TEXT_CONTENT.decode('utf-8'))

    def test_image_fingerprint_is_recoverable(self):
        order   = self.buy(self.image_product)
        content = self.download(self.image_product)
        found   = identify_content(content)
        self.assertIsNotNone(found)
        self.assertEqual((found.user, found.order, found.product), (self.user, order, self.image_product))

    def test_image_copy_keeps_size_and_is_visually_identical(self):
        self.buy(self.image_product)
        original = Image.open(io.BytesIO(png_bytes())).convert('RGB')
        copy     = Image.open(io.BytesIO(self.download(self.image_product))).convert('RGB')
        self.assertEqual(original.size, copy.size)
        differences = [
            abs(a - b)
            for pixel_a, pixel_b in zip(original.getdata(), copy.getdata())
            for a, b in zip(pixel_a, pixel_b)
        ]
        self.assertLessEqual(max(differences), 1)

    def test_original_file_is_not_modified(self):
        self.buy(self.text_product)
        self.download(self.text_product)
        with self.text_product.file_path.open('rb') as f:
            self.assertEqual(f.read(), TEXT_CONTENT)

    def test_repeated_downloads_reuse_fingerprint_and_count(self):
        self.buy(self.text_product)
        first  = self.download(self.text_product)
        second = self.download(self.text_product)
        self.assertEqual(first, second)
        self.assertEqual(FingerPrint.objects.filter(user=self.user, product=self.text_product).count(), 1)
        self.assertEqual(Download.objects.get(user=self.user, product=self.text_product).download_count, 2)

    def test_each_buyer_gets_a_different_fingerprint(self):
        self.buy(self.text_product)
        first = self.download(self.text_product)
        other = User.objects.create_user(email='otro@test.com', password=self.PASSWORD, name='Otro')
        self.client.force_login(other)
        self.user = other
        self.buy(self.text_product)
        second = self.download(self.text_product)
        self.assertNotEqual(first, second)
        self.assertEqual(identify_content(second).user, other)

    def test_file_without_fingerprint_is_not_identified(self):
        self.assertIsNone(identify_content(TEXT_CONTENT))
        self.assertIsNone(identify_content(png_bytes()))

    def test_library_lists_only_purchased_products(self):
        self.buy(self.text_product)
        response = self.client.get(reverse('downloads:library'))
        self.assertContains(response, 'Manual')
        self.assertNotContains(response, 'Imagen de prueba')

    def test_identify_copy_command_reports_user_and_order(self):
        order = self.buy(self.text_product)
        path  = f'{MEDIA}/copia_sospechosa.txt'
        with open(path, 'wb') as f:
            f.write(self.download(self.text_product))
        out = io.StringIO()
        call_command('identify_copy', path, stdout=out)
        self.assertIn(self.user.email, out.getvalue())
        self.assertIn(f'Orden   : {order.pk}', out.getvalue())