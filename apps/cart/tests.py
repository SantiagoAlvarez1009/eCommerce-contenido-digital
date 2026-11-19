"""
Tests for the cart module
    add, remove and clear products, total,
    and that each user only works with their own cart.
"""
from decimal import Decimal

from django.test import Client
from django.urls import reverse

from apps.products.models  import DigitalProduct
from apps.services.testing import AppTestCase
from .models               import Cart, CartProducts


class CartTestCase(AppTestCase):

    def setUp(self):
        self.user    = self.make_user()
        self.manual  = self.make_product('Manual', price='10.00')
        self.guia    = self.make_product('Guia'  , price='5.50')
        self.client.force_login(self.user)

    def cart(self, user=None):
        return Cart.objects.get(user=user or self.user)

    def in_cart(self, product, user=None):
        return self.cart(user).products.filter(pk=product.pk).exists()

    def add(self, product, client=None, **data):
        return (client or self.client).post(reverse('cart:add', args=[product.pk]), data)


class CartAccessTests(CartTestCase):

    def test_cart_requires_login(self):
        self.client.logout()
        urls = [
            ('get' , reverse('cart:detail')),
            ('post', reverse('cart:add'   , args=[self.manual.pk])),
            ('post', reverse('cart:remove', args=[self.manual.pk])),
            ('post', reverse('cart:clear')),
        ]
        for method, url in urls:
            with self.subTest(url=url):
                self.assertRedirectsToLogin(getattr(self.client, method)(url))
        self.assertFalse(CartProducts.objects.exists())

    def test_cart_actions_require_post(self):
        for url in (reverse('cart:add', args=[self.manual.pk]), reverse('cart:remove', args=[self.manual.pk]), reverse('cart:clear')):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 405)
        self.assertFalse(self.in_cart(self.manual))

    def test_each_user_only_sees_and_changes_their_own_cart(self):
        self.add(self.manual)

        other        = self.make_user('otro@test.com')
        other_client = Client()
        other_client.force_login(other)

        self.assertNotContains(other_client.get(reverse('cart:detail')), self.manual.name)
        other_client.post(reverse('cart:clear'))
        other_client.post(reverse('cart:remove', args=[self.manual.pk]))
        self.assertTrue(self.in_cart(self.manual))


class CartOperationsTests(CartTestCase):

    def test_add_product(self):
        response = self.add(self.manual)
        self.assertRedirects(response, reverse('cart:detail'))
        self.assertTrue(self.in_cart(self.manual))

    def test_adding_twice_keeps_a_single_item(self):
        self.add(self.manual)
        self.add(self.manual)
        self.assertEqual(self.cart().count, 1)

    def test_unavailable_product_cannot_be_added(self):
        hidden = self.make_product('Oculto', status=DigitalProduct.Status.NOT_AVAILABLE)
        self.add(hidden)
        self.assertFalse(self.in_cart(hidden))

    def test_nonexistent_product_returns_404(self):
        response = self.client.post(reverse('cart:add', args=[9999]))
        self.assertEqual(response.status_code, 404)

    def test_already_purchased_product_cannot_be_added_again(self):
        self.buy(self.manual)
        self.add(self.manual)
        self.assertFalse(self.in_cart(self.manual))

    def test_remove_product(self):
        self.add(self.manual)
        self.add(self.guia)
        self.client.post(reverse('cart:remove', args=[self.manual.pk]))
        self.assertFalse(self.in_cart(self.manual))
        self.assertTrue(self.in_cart(self.guia))

    def test_clear_cart(self):
        self.add(self.manual)
        self.add(self.guia)
        self.client.post(reverse('cart:clear'))
        self.assertEqual(self.cart().count, 0)

    def test_total_and_count(self):
        self.add(self.manual)
        self.add(self.guia)
        cart = self.cart()
        self.assertEqual(cart.count, 2)
        self.assertEqual(cart.total, Decimal('15.50'))

    def test_cart_page_lists_products(self):
        self.add(self.manual)
        self.add(self.guia)
        response = self.client.get(reverse('cart:detail'))
        self.assertContains(response, self.manual.name)
        self.assertContains(response, self.guia.name)

    def test_checkout_empties_the_cart(self):
        self.add(self.manual)
        self.client.post(reverse('orders:checkout'))
        self.assertEqual(self.cart().count, 0)


class CartRedirectTests(CartTestCase):
    """The optional "next" parameter only allows redirects inside the site."""

    def test_internal_next_is_followed(self):
        next_url = reverse('catalog:detail', args=[self.manual.pk])
        response = self.add(self.manual, next=next_url)
        self.assertRedirects(response, next_url)

    def test_external_next_is_ignored(self):
        for next_url in ('https://sitio-malicioso.com/', '//sitio-malicioso.com/'):
            with self.subTest(next=next_url):
                response = self.add(self.guia, next=next_url)
                self.assertRedirects(response, reverse('cart:detail'))