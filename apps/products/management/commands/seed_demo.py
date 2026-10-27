from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand

from apps.cart.models import Cart
from apps.products.models import DigitalProduct
from apps.users.models import User

USERS = [
    ('admin@demo.test',    'Admin Demo',    User.Role.ADMIN),
    ('operador@demo.test', 'Operador Demo', User.Role.OPERATOR),
    ('cliente@demo.test',  'Cliente Demo',  User.Role.CLIENT),
]
PASSWORD = 'Demo-Pass-12345'

PRODUCTS = [
    ('Manual de Redes',        'Manual introductorio de redes de computadoras.', '19.99'),
    ('Guia de Criptografia',   'Guia practica de criptografia aplicada.',        '24.50'),
    ('Apuntes de Seguridad',   'Apuntes del curso de seguridad informatica.',    '9.90'),
]


class Command(BaseCommand):
    help = 'Create demo users (one per role) and sample digital products.'

    def handle(self, *args, **options):
        for email, name, role in USERS:
            user, created = User.objects.get_or_create(
                email=email,
                defaults={'name': name, 'role': role, 'is_staff': role == User.Role.ADMIN},
            )
            if created:
                user.set_password(PASSWORD)
                user.save()
            Cart.objects.get_or_create(user=user)
            self.stdout.write(f'{"Creado" if created else "Existe"}: {email} ({role})')

        for name, description, price in PRODUCTS:
            if DigitalProduct.objects.filter(name=name).exists():
                continue
            product = DigitalProduct(name=name, description=description, price=price)
            body = f'{name}\n\n{description}\n\nContenido de demostracion.\n'.encode('utf-8')
            product.file_path.save(f'{name.lower().replace(" ", "_")}.txt', ContentFile(body), save=False)
            product.save()
            self.stdout.write(f'Producto creado: {name}')

        self.stdout.write(self.style.SUCCESS(f'Listo. Contrasena de los usuarios demo: {PASSWORD}'))
