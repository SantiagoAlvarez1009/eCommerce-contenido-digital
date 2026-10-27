from django.core.management.base import BaseCommand, CommandError

from apps.downloads.services import identify_content


class Command(BaseCommand):
    help = 'Identify the user and order of a downloaded copy from its fingerprint.'

    def add_arguments(self, parser):
        parser.add_argument('path', help='Path of the suspicious copy.')

    def handle(self, *args, **options):
        try:
            with open(options['path'], 'rb') as f:
                data = f.read()
        except OSError as exc:
            raise CommandError(f'No se pudo leer el archivo: {exc}')

        fp = identify_content(data)
        if fp is None:
            self.stdout.write(self.style.WARNING('No se encontro ningun fingerprint reconocido.'))
            return

        self.stdout.write(self.style.SUCCESS(f'Fingerprint: {fp.fingerprint}'))
        self.stdout.write(f'Usuario : {fp.user.email} (id {fp.user_id})')
        self.stdout.write(f'Orden   : {fp.order_id}')
        self.stdout.write(f'Producto: {fp.product.name} (id {fp.product_id})')
        self.stdout.write(f'Creado  : {fp.created_at:%Y-%m-%d %H:%M:%S}')
