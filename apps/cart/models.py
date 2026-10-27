from decimal import Decimal

from django.db import models


class Cart(models.Model):
    user = models.OneToOneField(
        'users.User',
        on_delete    = models.CASCADE,
        related_name = 'cart'
    )
    products = models.ManyToManyField(
        'products.DigitalProduct',
        through      = 'CartProducts',
        related_name = 'carts'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f'Cart #{self.pk} - {self.user}'

    @property
    def total(self):
        return sum((p.price for p in self.products.all()), Decimal('0.00'))

    @property
    def count(self):
        return self.products.count()

    def add(self, product):
        item, created = CartProducts.objects.get_or_create(cart=self, product=product)
        return created

    def remove(self, product):
        CartProducts.objects.filter(cart=self, product=product).delete()

    def clear(self):
        CartProducts.objects.filter(cart=self).delete()


class CartProducts(models.Model):
    cart = models.ForeignKey(
        Cart,
        on_delete = models.CASCADE
    )
    product = models.ForeignKey(
        'products.DigitalProduct',
        on_delete = models.CASCADE
    )
    added_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ('cart', 'product')
