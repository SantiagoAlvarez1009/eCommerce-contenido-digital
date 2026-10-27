from django.core.paginator import Paginator
from django.db.models      import Q
from django.shortcuts      import get_object_or_404, render

from apps.products.models import DigitalProduct
from apps.orders.services  import user_owns_product

PAGE_SIZE = 12


def product_list(request):
    products = DigitalProduct.objects.filter(status=DigitalProduct.Status.AVAILABLE)
    query    = request.GET.get('q', '').strip()
    if query:
        products = products.filter(Q(name__icontains=query) | Q(description__icontains=query))

    page = Paginator(products.order_by('-created_at'), PAGE_SIZE).get_page(request.GET.get('page'))
    return render(request, 'catalog/list.html', {'page': page, 'query': query})


def product_detail(request, pk):
    product = get_object_or_404(DigitalProduct, pk=pk, status=DigitalProduct.Status.AVAILABLE)
    owned   = request.user.is_authenticated and user_owns_product(request.user, product)
    return render(request, 'catalog/detail.html', {'product': product, 'owned': owned})
