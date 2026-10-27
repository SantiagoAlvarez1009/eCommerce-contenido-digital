import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test            import TestCase, override_settings
from django.urls            import reverse

from apps.cart.models        import Cart
from apps.downloads.models   import Download, FingerPrint
from apps.downloads.services import identify_content
from apps.payments.models    import Payment, PaymentReceipt
from apps.products.models    import DigitalProduct
from apps.users.models       import User
from .models                 import Order

MEDIA = tempfile.mkdtemp()


@override_settings(MEDIA_ROOT=MEDIA)
class PurchaseFlowTests(TestCase):
    PASSWORD = 'Una-Clave-Larga-98765'

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        self.product = DigitalProduct(name='Manual', description='Manual de prueba', price='10.50')
        self.product.file_path.save('manual.txt', ContentFile(b'contenido original'), save=False)
        self.product.save()
        self.other = DigitalProduct(name='Guia', description='Guia de prueba', price='5.00')
        self.other.file_path.save('guia.txt', ContentFile(b'otra cosa'), save=False)
        self.other.save()

    def register(self, email='ana@test.com'):
        response = self.client.post(reverse('users:register'), {
            'email': email, 'name': 'Ana', 'password1': self.PASSWORD, 'password2': self.PASSWORD,
        })
        self.assertRedirects(response, reverse('catalog:list'))
        return User.objects.get(email=email)

    def buy(self, product, approve=True):
        self.client.post(reverse('cart:add', args=[product.pk]))
        self.client.post(reverse('orders:checkout'))
        order = Order.objects.filter(products=product).latest('created_at')
        self.client.post(reverse('payments:pay', args=[order.pk]), {'result': 'approved' if approve else 'failed'})
        order.refresh_from_db()
        return order

    def test_registration_stores_hash_and_creates_session(self):
        user = self.register()
        self.assertNotEqual(user.password, self.PASSWORD)
        self.assertTrue(user.check_password(self.PASSWORD))
        self.assertEqual(user.role, User.Role.CLIENT)

    def test_login_with_email(self):
        user = User.objects.create_user('luis@test.com', self.PASSWORD, name='Luis')
        self.assertTrue(self.client.login(email=user.email, password=self.PASSWORD))
        self.assertFalse(self.client.login(email=user.email, password='incorrecta'))

    def test_catalog_lists_only_available_products(self):
        self.other.status = DigitalProduct.Status.NOT_AVAILABLE
        self.other.save()
        response = self.client.get(reverse('catalog:list'))
        self.assertContains(response, 'Manual')
        self.assertNotContains(response, 'Guia')

    def test_product_hash_is_computed_on_upload(self):
        self.assertEqual(len(self.product.file_hash), 64)
        self.assertTrue(self.product.file_is_intact())

    def test_full_purchase_and_download_flow(self):
        user = self.register()
        order = self.buy(self.product)

        self.assertEqual(order.status, Order.Status.COMPLETED)
        self.assertEqual(str(order.total), '10.50')
        self.assertEqual(Cart.objects.get(user=user).count, 0)
        self.assertEqual(Payment.objects.get(order=order).status, Payment.Status.COMPLETED)
        receipt = PaymentReceipt.objects.get(payment__order=order)
        self.assertIn(Payment.objects.get(order=order).transaction_reference, receipt.read_text())

        response = self.client.get(reverse('downloads:download', args=[self.product.pk]))
        self.assertEqual(response.status_code, 200)
        content = b''.join(response.streaming_content)
        self.assertTrue(content.startswith(b'contenido original'))

        found = identify_content(content)
        self.assertEqual((found.user, found.order), (user, order))
        self.assertEqual(Download.objects.get(user=user, product=self.product).download_count, 1)

        self.client.get(reverse('downloads:download', args=[self.product.pk]))
        self.assertEqual(Download.objects.get(user=user, product=self.product).download_count, 2)
        self.assertEqual(FingerPrint.objects.filter(user=user).count(), 1)

    def test_failed_payment_keeps_order_pending_and_blocks_download(self):
        self.register()
        order = self.buy(self.product, approve=False)
        self.assertEqual(order.status, Order.Status.PENDING)
        self.assertFalse(PaymentReceipt.objects.exists())
        response = self.client.get(reverse('downloads:download', args=[self.product.pk]))
        self.assertRedirects(response, reverse('downloads:library'))

    def test_order_keeps_price_at_purchase_time(self):
        self.register()
        order = self.buy(self.product)
        self.product.price = '99.00'
        self.product.save()
        self.assertEqual(str(order.items.get().price), '10.50')

    def test_client_cannot_see_other_clients_orders(self):
        self.register('ana@test.com')
        order = self.buy(self.product)
        self.client.logout()
        self.register('beto@test.com')
        self.assertEqual(self.client.get(reverse('orders:detail', args=[order.pk])).status_code, 404)
        self.assertEqual(self.client.get(reverse('downloads:download', args=[self.product.pk])).status_code, 302)

    def test_already_owned_product_is_not_added_again(self):
        user = self.register()
        self.buy(self.product)
        self.client.post(reverse('cart:add', args=[self.product.pk]))
        self.assertEqual(Cart.objects.get(user=user).count, 0)

    def test_empty_cart_cannot_checkout(self):
        self.register()
        response = self.client.post(reverse('orders:checkout'))
        self.assertRedirects(response, reverse('cart:detail'))
        self.assertEqual(Order.objects.count(), 0)

    def test_operator_manages_products_and_orders_client_cannot(self):
        client_user = self.register()
        self.client.logout()
        operator = User.objects.create_user('op@test.com', self.PASSWORD, name='Op', role=User.Role.OPERATOR)

        self.client.force_login(client_user)
        self.assertEqual(self.client.get(reverse('products:list')).status_code, 403)

        self.client.force_login(operator)
        self.assertEqual(self.client.get(reverse('products:list')).status_code, 200)
        self.client.post(reverse('products:toggle', args=[self.product.pk]))
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, DigitalProduct.Status.NOT_AVAILABLE)
        self.assertEqual(self.client.get(reverse('orders:manage_list')).status_code, 200)
        self.assertEqual(self.client.get(reverse('users:manage_list')).status_code, 403)

    def test_admin_changes_role_and_disables_account(self):
        admin  = User.objects.create_user('adm@test.com', self.PASSWORD, name='Adm', role=User.Role.ADMIN)
        target = User.objects.create_user('t@test.com', self.PASSWORD, name='T')
        self.client.force_login(admin)

        self.client.post(reverse('users:manage_role', args=[target.pk]), {'role': User.Role.OPERATOR})
        self.client.post(reverse('users:manage_toggle', args=[target.pk]))
        target.refresh_from_db()
        self.assertEqual(target.role, User.Role.OPERATOR)
        self.assertFalse(target.is_active)
        self.assertEqual(target.status, User.Status.INACTIVE)

    def test_password_reset_email_is_sent_and_token_is_single_use(self):
        from django.core import mail
        import re
        User.objects.create_user('rec@test.com', self.PASSWORD, name='Rec')
        self.client.post(reverse('users:password_reset'), {'email': 'rec@test.com'})
        self.assertEqual(len(mail.outbox), 1)

        path = re.search(r'https?://[^/]+(/\S+)', mail.outbox[0].body).group(1)
        response = self.client.get(path, follow=True)
        post_url = response.redirect_chain[-1][0]
        new_password = 'Otra-Clave-Larga-4321'
        self.client.post(post_url, {'new_password1': new_password, 'new_password2': new_password})
        self.assertTrue(User.objects.get(email='rec@test.com').check_password(new_password))

        again = self.client.get(path, follow=True)
        self.assertFalse(again.context['validlink'])

    def test_every_page_renders(self):
        admin = User.objects.create_user('all@test.com', self.PASSWORD, name='All', role=User.Role.ADMIN)
        self.client.force_login(admin)
        order = self.buy(self.product)
        receipt = PaymentReceipt.objects.get(payment__order=order)
        pending = Order.objects.create(user=admin, total='5.00')
        self.client.post(reverse('cart:add', args=[self.other.pk]))

        urls = [
            reverse('catalog:list'), reverse('catalog:detail', args=[self.product.pk]),
            reverse('cart:detail'), reverse('orders:list'), reverse('orders:detail', args=[order.pk]),
            reverse('payments:pay', args=[pending.pk]), reverse('payments:receipts'),
            reverse('payments:receipt_detail', args=[receipt.pk]),
            reverse('payments:receipt_download', args=[receipt.pk]),
            reverse('downloads:library'), reverse('users:profile'),
            reverse('users:manage_list'), reverse('products:list'), reverse('products:create'),
            reverse('products:edit', args=[self.product.pk]),
            reverse('orders:manage_list'), reverse('orders:manage_detail', args=[order.pk]),
            reverse('users:password_reset'), reverse('users:login'), reverse('users:register'),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertIn(self.client.get(url, follow=True).status_code, (200,))

    def test_operator_creates_product_through_form(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        operator = User.objects.create_user('op2@test.com', self.PASSWORD, name='Op', role=User.Role.OPERATOR)
        self.client.force_login(operator)
        response = self.client.post(reverse('products:create'), {
            'name': 'Nuevo', 'description': 'Desc', 'price': '3.00', 'status': 'disponible',
            'file_path': SimpleUploadedFile('nuevo.txt', b'abc'),
        })
        self.assertRedirects(response, reverse('products:list'))
        product = DigitalProduct.objects.get(name='Nuevo')
        self.assertEqual(product.file_name, 'nuevo.txt')
        self.assertEqual(product.file_hash, 'ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad')
