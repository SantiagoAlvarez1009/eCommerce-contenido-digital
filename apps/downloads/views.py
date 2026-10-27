import io
import mimetypes

from django.contrib                 import messages
from django.contrib.auth.decorators import login_required
from django.http                    import FileResponse
from django.shortcuts               import get_object_or_404, redirect, render

from apps.orders.services import purchased_products
from apps.products.models import DigitalProduct
from .models   import Download
from .services import NotPurchasedError, prepare_download


@login_required
def library(request):
    products  = purchased_products(request.user)
    counts    = dict(Download.objects.filter(user=request.user).values_list('product_id', 'download_count'))
    return render(request, 'downloads/library.html', {
        'items': [(product, counts.get(product.pk, 0)) for product in products],
    })


@login_required
def download_product(request, product_id):
    product = get_object_or_404(DigitalProduct, pk=product_id)
    try:
        content, file_name, _fingerprint = prepare_download(request.user, product)
    except NotPurchasedError:
        messages.error(request, 'Solo puedes descargar productos que hayas adquirido.')
        return redirect('downloads:library')

    return FileResponse(
        io.BytesIO(content),
        as_attachment = True,
        filename      = file_name,
        content_type  = mimetypes.guess_type(file_name)[0] or 'application/octet-stream'
    )
