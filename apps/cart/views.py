from django.contrib                 import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts               import get_object_or_404, redirect, render
from django.utils.http              import url_has_allowed_host_and_scheme
from django.views.decorators.http   import require_POST

from apps.orders.services  import user_owns_product
from apps.products.models  import DigitalProduct
from .models               import Cart


def _get_cart(user):
    cart, _ = Cart.objects.get_or_create(user=user)
    return cart


@login_required
def cart_detail(request):
    cart = _get_cart(request.user)
    return render(request, 'cart/detail.html', {
        'cart'    : cart,
        'products': cart.products.all(),
    })


@login_required
@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(DigitalProduct, pk=product_id)
    if not product.is_available:
        messages.error(request, 'El producto no esta disponible.')
    elif user_owns_product(request.user, product):
        messages.info(request, 'Ya adquiriste este producto.')
    elif _get_cart(request.user).add(product):
        messages.success(request, f'"{product.name}" agregado al carrito.')
    else:
        messages.info(request, 'El producto ya estaba en el carrito.')
    next_url = request.POST.get('next', '')
    if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        return redirect(next_url)
    return redirect('cart:detail')


@login_required
@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(DigitalProduct, pk=product_id)
    _get_cart(request.user).remove(product)
    messages.success(request, f'"{product.name}" quitado del carrito.')
    return redirect('cart:detail')


@login_required
@require_POST
def cart_clear(request):
    _get_cart(request.user).clear()
    messages.success(request, 'Carrito vaciado.')
    return redirect('cart:detail')
