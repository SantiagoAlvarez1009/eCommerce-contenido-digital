"""
Tests for the public catalog
    listing, search, pagination and product detail.
These are public functions (no login required).
"""
from django.urls import reverse

from apps.products.models  import DigitalProduct
from apps.services.testing import AppTestCase
from .views                import PAGE_SIZE

Status = DigitalProduct.Status


class CatalogListTests(AppTestCase):

    def setUp(self):
        self.manual = self.make_product('Manual de Redes')
        self.guia   = self.make_product('Guia de Criptografia')
        self.hidden = self.make_product('Producto Oculto', status=Status.NOT_AVAILABLE)

    def test_catalog_is_public(self):
        response = self.client.get(reverse('catalog:list'))
        self.assertEqual(response.status_code, 200)

    def test_catalog_lists_only_available_products(self):
        response = self.client.get(reverse('catalog:list'))
        self.assertContains(response, self.manual.name)
        self.assertContains(response, self.guia.name)
        self.assertNotContains(response, self.hidden.name)

    def test_deactivated_product_disappears_from_catalog(self):
        self.manual.status = Status.NOT_AVAILABLE
        self.manual.save()
        self.assertNotContains(self.client.get(reverse('catalog:list')), self.manual.name)

    def test_search_by_name(self):
        response = self.client.get(reverse('catalog:list'), {'q': 'redes'})
        self.assertContains(response, self.manual.name)
        self.assertNotContains(response, self.guia.name)

    def test_search_by_description(self):
        # make_product uses "<name> de prueba" as description.
        response = self.client.get(reverse('catalog:list'), {'q': 'Criptografia de prueba'})
        self.assertContains(response, self.guia.name)
        self.assertNotContains(response, self.manual.name)

    def test_search_does_not_reveal_unavailable_products(self):
        response = self.client.get(reverse('catalog:list'), {'q': 'Oculto'})
        self.assertNotContains(response, self.hidden.name)

    def test_search_with_special_characters_does_not_fail(self):
        for query in ("' OR 1=1 --", '<script>alert(1)</script>', '%_'):
            with self.subTest(query=query):
                response = self.client.get(reverse('catalog:list'), {'q': query})
                self.assertEqual(response.status_code, 200)
                self.assertNotContains(response, '<script>alert(1)</script>')

    def test_catalog_is_paginated(self):
        for i in range(PAGE_SIZE):
            self.make_product(f'Extra {i}')
        first  = self.client.get(reverse('catalog:list'))
        second = self.client.get(reverse('catalog:list'), {'page': 2})
        self.assertEqual(len(first.context['page']), PAGE_SIZE)
        self.assertEqual(len(second.context['page']), 2)  # 14 available products in total

    def test_invalid_page_does_not_fail(self):
        response = self.client.get(reverse('catalog:list'), {'page': 'abc'})
        self.assertEqual(response.status_code, 200)


class CatalogDetailTests(AppTestCase):

    def setUp(self):
        self.product = self.make_product('Manual')

    def detail(self, product=None):
        return self.client.get(reverse('catalog:detail', args=[(product or self.product).pk]))

    def test_detail_shows_product_information(self):
        response = self.detail()
        self.assertContains(response, self.product.name)
        self.assertContains(response, self.product.description)
        self.assertRegex(response.content.decode(), r'\$10[.,]00')

    def test_detail_does_not_expose_file_location(self):
        response = self.detail()
        self.assertNotContains(response, self.product.file_path.url)
        self.assertNotContains(response, 'digital_products/')

    def test_unavailable_product_detail_returns_404(self):
        hidden = self.make_product('Oculto', status=Status.NOT_AVAILABLE)
        self.assertEqual(self.detail(hidden).status_code, 404)

    def test_nonexistent_product_returns_404(self):
        self.assertEqual(self.client.get(reverse('catalog:detail', args=[9999])).status_code, 404)

    def test_anonymous_is_invited_to_log_in(self):
        response = self.detail()
        self.assertContains(response, 'Inicia sesión para comprar')
        self.assertNotContains(response, reverse('cart:add', args=[self.product.pk]))

    def test_logged_in_client_can_add_to_cart(self):
        self.client.force_login(self.make_user())
        self.assertContains(self.detail(), reverse('cart:add', args=[self.product.pk]))

    def test_owner_sees_download_instead_of_buy(self):
        self.client.force_login(self.make_user())
        self.buy(self.product)
        response = self.detail()
        self.assertContains(response, reverse('downloads:download', args=[self.product.pk]))
        self.assertNotContains(response, reverse('cart:add', args=[self.product.pk]))

    def test_failed_payment_does_not_grant_download(self):
        self.client.force_login(self.make_user())
        self.buy(self.product, approve=False)
        self.assertNotContains(self.detail(), reverse('downloads:download', args=[self.product.pk]))