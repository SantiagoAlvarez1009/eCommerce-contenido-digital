"""
Helpers for the test suite
"""
import shutil
import tempfile

from django.core.files.base import ContentFile
from django.test            import TestCase, override_settings
from django.urls            import reverse

from apps.cart.models     import Cart
from apps.orders.models   import Order
from apps.products.models import DigitalProduct
from apps.users.models    import User

PASSWORD = 'Contra-Super-Secreta-007'
Role     = User.Role


def make_user(email='cliente@test.com', role=Role.CLIENT, password=PASSWORD, name=None, **extra):
    """Create a user a given role (client by default) and its cart."""
    user = User.objects.create_user(
        email    = email,
        password = password,
        name     = name or email.split('@')[0].capitalize(),
        role     = role,
        **extra
    )
    Cart.objects.get_or_create(user=user)
    return user


def make_product(name='Manual', price='10.00', content=b'contenido original', status=None, file_name=None):
    """Create a .txt digital product stored in MEDIA_ROOT."""
    product = DigitalProduct(name=name, description=f'{name} de prueba', price=price)
    if status:
        product.status = status
    product.file_path.save(file_name or f'{name.lower().replace(" ", "_")}.txt', ContentFile(content), save=False)
    product.save()
    return product


def buy(client, products, approve=True):
    """
    Run the purchase flow through the views with an already logged-in client:
    add to cart -> checkout -> simulated payment. Returns the created order.
    """
    if isinstance(products, DigitalProduct):
        products = [products]
    for product in products:
        client.post(reverse('cart:add', args=[product.pk]))
    client.post(reverse('orders:checkout'))
    order = Order.objects.filter(user_id=client.session['_auth_user_id']).latest('created_at')
    client.post(reverse('payments:pay', args=[order.pk]), {'result': 'approved' if approve else 'failed'})
    order.refresh_from_db()
    return order


class AppTestCase(TestCase):
    """
    TestCase with an isolated temporary MEDIA_ROOT and shortcuts for the most common setup.
    """

    @classmethod
    def setUpClass(cls):
        cls._media_dir      = tempfile.mkdtemp()
        cls._media_override = override_settings(MEDIA_ROOT=cls._media_dir)
        cls._media_override.enable()
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        cls._media_override.disable()
        shutil.rmtree(cls._media_dir, ignore_errors=True)

    # Shortcuts so tests read as self.make_user(...), self.buy(...)
    make_user    = staticmethod(make_user)
    make_product = staticmethod(make_product)

    def buy(self, products, approve=True, client=None):
        return buy(client or self.client, products, approve)

    def make_users_for_every_role(self):
        """Create self.customer, self.operator and self.admin."""
        self.customer = make_user('cliente@test.com' , Role.CLIENT)
        self.operator = make_user('operador@test.com', Role.OPERATOR)
        self.admin    = make_user('admin@test.com'   , Role.ADMIN)

    def assertForbidden(self, response):
        self.assertEqual(response.status_code, 403)

    def assertRedirectsToLogin(self, response):
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('users:login'), response.url)

    def is_logged_in(self, client=None):
        return '_auth_user_id' in (client or self.client).session