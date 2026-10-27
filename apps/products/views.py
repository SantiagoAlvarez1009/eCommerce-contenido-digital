from django.contrib               import messages
from django.shortcuts             import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.services.permissions.roles import role_required
from apps.users.models               import User
from .forms  import ProductForm
from .models import DigitalProduct

OPERATOR_ROLES = (User.Role.OPERATOR, User.Role.ADMIN)


@role_required(*OPERATOR_ROLES)
def product_list(request):
    return render(request, 'products/list.html', {'products': DigitalProduct.objects.all()})


@role_required(*OPERATOR_ROLES)
def product_create(request):
    form = ProductForm(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        product = form.save()
        messages.success(request, f'Producto "{product.name}" registrado.')
        return redirect('products:list')
    return render(request, 'products/form.html', {'form': form, 'title': 'Registrar producto'})


@role_required(*OPERATOR_ROLES)
def product_edit(request, pk):
    product = get_object_or_404(DigitalProduct, pk=pk)
    form    = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, f'Producto "{product.name}" actualizado.')
        return redirect('products:list')
    return render(request, 'products/form.html', {'form': form, 'title': f'Editar: {product.name}'})


@role_required(*OPERATOR_ROLES)
@require_POST
def product_toggle(request, pk):
    product = get_object_or_404(DigitalProduct, pk=pk)
    product.status = (
        DigitalProduct.Status.NOT_AVAILABLE if product.is_available else DigitalProduct.Status.AVAILABLE
    )
    product.save(update_fields=['status'])
    messages.success(request, f'"{product.name}": {product.get_status_display()}.')
    return redirect('products:list')
