from django.core.management.base import BaseCommand, CommandError

from apps.products.models import DigitalProduct


class Command(BaseCommand):
    help = 'Verifica que el archivo de cada producto coincida con su hash SHA-256 registrado.'

    def handle(self, *args, **options):
        altered = []
        for product in DigitalProduct.objects.order_by('pk'):
            try:
                current = product.current_file_hash()
            except (OSError, ValueError):
                current = None
            if current and current == product.file_hash:
                self.stdout.write(self.style.SUCCESS(f'OK        {product.name}'))
            else:
                altered.append(product.name)
                self.stdout.write(self.style.ERROR(f'ALTERADO  {product.name}'))
                self.stdout.write(f'          registrado: {product.file_hash}')
                self.stdout.write(f'          actual    : {current or "archivo no disponible"}')
        if altered:
            raise CommandError(f'{len(altered)} producto(s) con integridad fallida.')
        self.stdout.write(self.style.SUCCESS('Todos los productos coinciden con su hash.'))
