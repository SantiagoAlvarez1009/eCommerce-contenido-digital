from .models import CartProducts


def cart_count(request):
    """Number of products in the authenticated user's cart, for the navbar."""
    if not request.user.is_authenticated:
        return {'cart_count': 0}
    return {'cart_count': CartProducts.objects.filter(cart__user=request.user).count()}
