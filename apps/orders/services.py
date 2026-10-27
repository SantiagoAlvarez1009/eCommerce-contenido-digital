from django.db import transaction

from apps.cart.models     import Cart
from apps.products.models import DigitalProduct
from .models              import Order, OrderProducts


class EmptyOrderError(Exception):
    """The cart has no products that can be purchased."""


def purchased_products(user):
    """Products the user owns: those in orders already paid (completed)."""
    return DigitalProduct.objects.filter(
        orders__user   = user,
        orders__status = Order.Status.COMPLETED
    ).distinct()


def user_owns_product(user, product):
    return purchased_products(user).filter(pk=product.pk).exists()


def purchase_order_for(user, product):
    """Most recent paid order of the user that contains the product, or None."""
    return Order.objects.filter(
        user     = user,
        status   = Order.Status.COMPLETED,
        products = product
    ).order_by('-created_at').first()


@transaction.atomic
def create_order_from_cart(user):
    """
    Turn the user's cart into an order, freezing the price of each product.
    Unavailable products and products the user already owns are skipped.
    """
    cart, _ = Cart.objects.get_or_create(user=user)
    owned   = set(purchased_products(user).values_list('pk', flat=True))
    items = [
        product for product in cart.products.all()
        if product.is_available and product.pk not in owned
    ]
    if not items:
        raise EmptyOrderError('No hay productos disponibles para comprar en el carrito.')

    order = Order.objects.create(user=user, total=sum(p.price for p in items))
    OrderProducts.objects.bulk_create(
        OrderProducts(order=order, product=product, price=product.price)
        for product in items
    )
    cart.clear()
    return order


@transaction.atomic
def cancel_order(order):
    if order.is_paid:
        raise ValueError('Una orden pagada no puede cancelarse por el cliente.')
    order.status = Order.Status.CANCELLED
    order.save(update_fields=['status'])
    return order
