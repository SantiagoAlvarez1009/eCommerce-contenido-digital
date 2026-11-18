import io

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse
from PIL import Image, ImageDraw

from apps.cart.models import Cart
from apps.orders.models import Order
from apps.products.models import DigitalProduct
from apps.users.models import User

PASSWORD = 'Demo-Pass-12345'

EXTRA_CLIENTS = [
    ('maria@demo.test', 'Maria Demo'),
    ('juan@demo.test' , 'Juan Demo'),
]

IMAGE_PRODUCT = ('Infografia de Seguridad', 'Infografia sobre los servicios de seguridad.', '15.00')


def infographic_png():
    image = Image.new('RGB', (480, 320), (245, 243, 238))
    draw  = ImageDraw.Draw(image)
    colors = [(83, 74, 183), (15, 110, 86), (153, 60, 29), (24, 95, 165), (59, 109, 17)]
    labels = ['Confidencialidad', 'Integridad', 'Disponibilidad', 'Autenticacion', 'No repudio']
    for index, (color, label) in enumerate(zip(colors, labels)):
        top = 30 + index * 55
        draw.rectangle([40, top, 440, top + 40], fill=color)
        draw.text((56, top + 14), label, fill=(255, 255, 255))
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    return buffer.getvalue()


class Command(BaseCommand):
    help = 'Carga datos de prueba: clientes, ordenes en distintos estados, comprobantes firmados y descargas.'

    def handle(self, *args, **options):
        call_command('seed_demo', stdout=io.StringIO())

        if User.objects.filter(email=EXTRA_CLIENTS[0][0]).exists():
            self.stdout.write(self.style.WARNING('Los datos de prueba ya estaban cargados; no se duplicaron.'))
            return

        self.create_image_product()
        for email, name in EXTRA_CLIENTS:
            user = User.objects.create_user(email=email, password=PASSWORD, name=name)
            Cart.objects.get_or_create(user=user)

        manual    = DigitalProduct.objects.get(name='Manual de Redes')
        guia      = DigitalProduct.objects.get(name='Guia de Criptografia')
        apuntes   = DigitalProduct.objects.get(name='Apuntes de Seguridad')
        imagen    = DigitalProduct.objects.get(name=IMAGE_PRODUCT[0])

        cliente = self.session('cliente@demo.test')
        self.buy(cliente, [guia], approve=True, download=True)
        self.buy(cliente, [imagen], approve=True, download=True)
        self.buy(cliente, [manual], approve=None)

        maria = self.session('maria@demo.test')
        self.buy(maria, [manual, apuntes], approve=True, download=True)
        self.buy(maria, [guia], approve=False)

        juan = self.session('juan@demo.test')
        cancelled = self.buy(juan, [apuntes], approve=None)
        juan.post(reverse('orders:cancel', args=[cancelled.pk]), secure=True)
        processing = self.buy(juan, [imagen], approve=None)
        Order.objects.filter(pk=processing.pk).update(status=Order.Status.PROCESSING)

        self.session('juan@demo.test', password='contrasena-equivocada')

        self.report()

    def create_image_product(self):
        name, description, price = IMAGE_PRODUCT
        if DigitalProduct.objects.filter(name=name).exists():
            return
        product = DigitalProduct(name=name, description=description, price=price)
        product.file_path.save('infografia_de_seguridad.png', ContentFile(infographic_png()), save=False)
        product.save()

    def session(self, email, password=PASSWORD):
        host   = settings.ALLOWED_HOSTS[0] if settings.ALLOWED_HOSTS else 'localhost'
        client = Client(HTTP_HOST=host)
        client.post(reverse('users:login'), {'username': email, 'password': password}, secure=True)
        client.email = email
        return client

    def buy(self, client, products, approve, download=False):
        for product in products:
            client.post(reverse('cart:add', args=[product.pk]), secure=True)
        client.post(reverse('orders:checkout'), secure=True)
        order = Order.objects.filter(user__email=client.email).latest('created_at')
        if approve is not None:
            result = 'approved' if approve else 'failed'
            client.post(reverse('payments:pay', args=[order.pk]), {'result': result}, secure=True)
        if download:
            for product in products:
                response = client.get(reverse('downloads:download', args=[product.pk]), secure=True)
                b''.join(getattr(response, 'streaming_content', [b'']))
        return order

    def report(self):
        self.stdout.write(self.style.SUCCESS('Datos de prueba cargados.'))
        self.stdout.write(f'Contrasena de todos los usuarios: {PASSWORD}')
        for user in User.objects.filter(email__endswith='@demo.test').order_by('email'):
            orders = Order.objects.filter(user=user)
            summary = ', '.join(f'#{o.pk} {o.get_status_display()}' for o in orders.order_by('pk')) or 'sin ordenes'
            self.stdout.write(f'  {user.email:<22} {user.get_role_display():<14} {summary}')
