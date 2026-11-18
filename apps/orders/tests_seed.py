import io
import shutil
import tempfile

from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.downloads.models import FingerPrint
from apps.orders.models import Order
from apps.payments.models import PaymentReceipt
from apps.products.models import DigitalProduct
from apps.services.crypto import signing
from apps.users.models import User

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class SeedTestDataTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def seed(self):
        out = io.StringIO()
        call_command('seed_test_data', stdout=out)
        return out.getvalue()

    def test_creates_users_for_every_role(self):
        self.seed()
        self.assertTrue(User.objects.filter(role=User.Role.ADMIN).exists())
        self.assertTrue(User.objects.filter(role=User.Role.OPERATOR).exists())
        self.assertEqual(User.objects.filter(role=User.Role.CLIENT).count(), 3)

    def test_creates_orders_in_every_status(self):
        self.seed()
        statuses = set(Order.objects.values_list('status', flat=True))
        self.assertEqual(statuses, set(Order.Status.values))

    def test_paid_orders_have_valid_signed_receipts(self):
        self.seed()
        receipts = PaymentReceipt.objects.all()
        self.assertEqual(receipts.count(), Order.objects.filter(status=Order.Status.COMPLETED).count())
        for receipt in receipts:
            self.assertTrue(signing.verify(receipt.read_bytes(), receipt.signature))

    def test_downloads_include_text_and_image_fingerprints(self):
        self.seed()
        image = DigitalProduct.objects.get(name='Infografia de Seguridad')
        self.assertTrue(image.file_path.name.endswith('.png'))
        self.assertTrue(FingerPrint.objects.filter(product=image).exists())
        self.assertTrue(FingerPrint.objects.exclude(product=image).exists())

    def test_running_twice_does_not_duplicate_data(self):
        self.seed()
        orders = Order.objects.count()
        output = self.seed()
        self.assertEqual(Order.objects.count(), orders)
        self.assertIn('ya estaban cargados', output)
