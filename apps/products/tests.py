"""
Tests for the products module
    SHA-256 integrity of product files and
    catalog management by the OPERATOR role.
"""
import hashlib
import io

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls                    import reverse
from pypdf                          import PdfReader, PdfWriter

from apps.services.testing import AppTestCase, pdf_bytes, png_bytes
from apps.users.models     import User
from .forms                import (
    MAX_FILE_SIZE, MSG_CONTENT, MSG_ENCRYPTED, MSG_EXTENSION, MSG_INVALID, MSG_SIZE
)
from .models               import DigitalProduct

Role   = User.Role
Status = DigitalProduct.Status

CONTENT = b'contenido original'


def encrypted_pdf_bytes():
    writer = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf_bytes())))
    writer.encrypt('clave')
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class ProductIntegrityTests(AppTestCase):

    def setUp(self):
        self.product = self.make_product(content=CONTENT)

    def test_original_file_has_expected_hash(self):
        self.assertEqual(self.product.file_hash, hashlib.sha256(CONTENT).hexdigest())
        self.assertEqual(self.product.current_file_hash(), self.product.file_hash)
        self.assertTrue(self.product.file_is_intact())

    def test_modified_file_has_different_hash(self):
        with open(self.product.file_path.path, 'wb') as f:
            f.write(b'contenido alterado')
        self.assertNotEqual(self.product.current_file_hash(), self.product.file_hash)
        self.assertFalse(self.product.file_is_intact())

    def test_file_name_is_stored(self):
        self.assertEqual(self.product.file_name, 'manual.txt')


class ProductAccessTests(AppTestCase):
    """Only OPERATOR (and ADMIN) can manage the catalog."""

    def setUp(self):
        self.make_users_for_every_role()
        self.product = self.make_product()

    def management_actions(self):
        return [
            ('get' , reverse('products:list')),
            ('get' , reverse('products:create')),
            ('get' , reverse('products:edit'  , args=[self.product.pk])),
            ('post', reverse('products:toggle', args=[self.product.pk])),
        ]

    def test_anonymous_is_sent_to_login(self):
        for method, url in self.management_actions():
            with self.subTest(url=url):
                self.assertRedirectsToLogin(getattr(self.client, method)(url))

    def test_client_cannot_manage_products(self):
        self.client.force_login(self.customer)
        for method, url in self.management_actions():
            with self.subTest(url=url):
                self.assertForbidden(getattr(self.client, method)(url))
        self.product.refresh_from_db()
        self.assertEqual(self.product.status, Status.AVAILABLE)

    def test_client_cannot_change_price(self):
        self.client.force_login(self.customer)
        response = self.client.post(reverse('products:edit', args=[self.product.pk]), {
            'name': self.product.name, 'description': 'x', 'price': '0.01', 'status': Status.AVAILABLE,
        })
        self.assertForbidden(response)
        self.product.refresh_from_db()
        self.assertEqual(str(self.product.price), '10.00')

    def test_operator_can_open_management_pages(self):
        self.client.force_login(self.operator)
        for method, url in self.management_actions()[:3]:
            with self.subTest(url=url):
                self.assertEqual(getattr(self.client, method)(url).status_code, 200)

    def test_toggle_requires_post(self):
        self.client.force_login(self.operator)
        response = self.client.get(reverse('products:toggle', args=[self.product.pk]))
        self.assertEqual(response.status_code, 405)


class ProductManagementTests(AppTestCase):

    def setUp(self):
        self.operator = self.make_user('operador@test.com', Role.OPERATOR)
        self.client.force_login(self.operator)

    def form_data(self, **overrides):
        data = {
            'name'       : 'Nuevo',
            'description': 'Descripcion',
            'price'      : '3.00',
            'status'     : Status.AVAILABLE,
            'file_path'  : SimpleUploadedFile('nuevo.txt', b'abc', content_type='text/plain'),
        }
        data.update(overrides)
        return data

    def create(self, **overrides):
        return self.client.post(reverse('products:create'), self.form_data(**overrides))

    # --- Register ---

    def test_operator_registers_product_and_hash_is_computed(self):
        response = self.create()
        self.assertRedirects(response, reverse('products:list'))
        product = DigitalProduct.objects.get(name='Nuevo')
        self.assertEqual(product.file_name, 'nuevo.txt')
        self.assertEqual(product.file_hash, hashlib.sha256(b'abc').hexdigest())

    def test_pdf_and_png_products_are_accepted(self):
        for name, content in (('manual.pdf', pdf_bytes()), ('imagen.png', png_bytes())):
            with self.subTest(file=name):
                response = self.create(name=name, file_path=SimpleUploadedFile(name, content))
                self.assertRedirects(response, reverse('products:list'))
                product = DigitalProduct.objects.get(name=name)
                self.assertEqual(product.file_hash, hashlib.sha256(content).hexdigest())

    def test_extension_is_case_insensitive(self):
        response = self.create(file_path=SimpleUploadedFile('MANUAL.PDF', pdf_bytes()))
        self.assertRedirects(response, reverse('products:list'))

    def test_unsupported_extensions_are_rejected(self):
        for name in ('manual.docx', 'pagina.html', 'script.py', 'programa.exe', 'foto.jpg', 'sin_extension'):
            with self.subTest(file=name):
                response = self.create(file_path=SimpleUploadedFile(name, b'abc'))
                self.assertContains(response, MSG_EXTENSION)
        self.assertFalse(DigitalProduct.objects.exists())

    def test_content_must_match_extension(self):
        cases = (
            ('falso.txt', b'\x89PNG\r\n\x1a\n\xff\xfe\x00'),  # binary renamed to .txt
            ('falso.pdf', b'solo texto plano'),                 # text renamed to .pdf
            ('falso.png', pdf_bytes()),                         # PDF renamed to .png
        )
        for name, content in cases:
            with self.subTest(file=name):
                response = self.create(file_path=SimpleUploadedFile(name, content))
                self.assertContains(response, MSG_CONTENT)
        self.assertFalse(DigitalProduct.objects.exists())

    def test_corrupt_files_are_rejected(self):
        for name, content in (('roto.pdf', b'%PDF-1.4 basura'), ('roto.png', b'\x89PNG\r\n\x1a\nbasura')):
            with self.subTest(file=name):
                response = self.create(file_path=SimpleUploadedFile(name, content))
                self.assertContains(response, MSG_INVALID)
        self.assertFalse(DigitalProduct.objects.exists())

    def test_encrypted_pdf_is_rejected(self):
        response = self.create(file_path=SimpleUploadedFile('cifrado.pdf', encrypted_pdf_bytes()))
        self.assertContains(response, MSG_ENCRYPTED)
        self.assertFalse(DigitalProduct.objects.exists())

    def test_file_too_large_is_rejected(self):
        big      = SimpleUploadedFile('grande.txt', b'a' * (MAX_FILE_SIZE + 1))
        response = self.create(file_path=big)
        self.assertContains(response, MSG_SIZE)
        self.assertFalse(DigitalProduct.objects.exists())

    def test_product_requires_a_file(self):
        data = self.form_data()
        del data['file_path']
        self.client.post(reverse('products:create'), data)
        self.assertFalse(DigitalProduct.objects.exists())

    def test_negative_price_is_rejected(self):
        response = self.create(price='-1.00')
        self.assertContains(response, 'El precio no puede ser negativo.')
        self.assertFalse(DigitalProduct.objects.exists())

    def test_purchased_is_not_a_valid_product_status(self):
        self.create(status=Status.PURCHASED)
        self.assertFalse(DigitalProduct.objects.exists())

    # --- Modify ---

    def test_operator_changes_price_and_data(self):
        product = self.make_product()
        self.client.post(reverse('products:edit', args=[product.pk]), {
            'name': 'Manual v2', 'description': 'Nueva', 'price': '15.00', 'status': Status.AVAILABLE,
        })
        product.refresh_from_db()
        self.assertEqual(product.name, 'Manual v2')
        self.assertEqual(str(product.price), '15.00')

    def test_edit_without_new_file_keeps_file_and_hash(self):
        product  = self.make_product()
        old_hash = product.file_hash
        self.client.post(reverse('products:edit', args=[product.pk]), {
            'name': product.name, 'description': 'x', 'price': '12.00', 'status': Status.AVAILABLE,
        })
        product.refresh_from_db()
        self.assertEqual(product.file_hash, old_hash)
        self.assertTrue(product.file_is_intact())

    def test_edit_with_new_file_recomputes_hash(self):
        product = self.make_product()
        self.client.post(reverse('products:edit', args=[product.pk]), {
            'name': product.name, 'description': 'x', 'price': '10.00', 'status': Status.AVAILABLE,
            'file_path': SimpleUploadedFile('v2.txt', b'version 2'),
        })
        product.refresh_from_db()
        self.assertEqual(product.file_name, 'v2.txt')
        self.assertEqual(product.file_hash, hashlib.sha256(b'version 2').hexdigest())
        self.assertTrue(product.file_is_intact())

    # --- Activate / deactivate ---

    def test_operator_deactivates_and_reactivates_product(self):
        product = self.make_product()
        url     = reverse('products:toggle', args=[product.pk])

        self.client.post(url)
        product.refresh_from_db()
        self.assertEqual(product.status, Status.NOT_AVAILABLE)

        self.client.post(url)
        product.refresh_from_db()
        self.assertEqual(product.status, Status.AVAILABLE)

    def test_management_list_shows_every_product_and_its_hash(self):
        visible = self.make_product('Visible')
        hidden  = self.make_product('Oculto', status=Status.NOT_AVAILABLE)
        response = self.client.get(reverse('products:list'))
        self.assertContains(response, visible.name)
        self.assertContains(response, hidden.name)
        self.assertContains(response, visible.file_hash)