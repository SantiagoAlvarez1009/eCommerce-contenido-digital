from django.contrib                 import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts               import get_object_or_404, redirect, render
from django.views.decorators.http   import require_POST

from apps.services.permissions.roles import role_required
from apps.users.models               import User
from .forms    import OrderStatusForm
from .models   import Order
from .services import EmptyOrderError, cancel_order, create_order_from_cart


@login_required
@require_POST
def checkout(request):
    try:
        order = create_order_from_cart(request.user)
    except EmptyOrderError as exc:
        messages.error(request, str(exc))
        return redirect('cart:detail')
    messages.success(request, f'Orden #{order.pk} creada. Procede con el pago.')
    return redirect('payments:pay', order_id=order.pk)


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related('items__product')
    return render(request, 'orders/list.html', {'orders': orders})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'payments__receipts'),
        pk=pk, user=request.user
    )
    return render(request, 'orders/detail.html', {'order': order})


@login_required
@require_POST
def order_cancel(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    try:
        cancel_order(order)
        messages.success(request, f'Orden #{order.pk} cancelada.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('orders:detail', pk=order.pk)


# --- Order processing (OPERATOR role) ---

@role_required(User.Role.OPERATOR, User.Role.ADMIN)
def manage_list(request):
    orders = Order.objects.select_related('user').prefetch_related('items__product')
    status = request.GET.get('status')
    if status in Order.Status.values:
        orders = orders.filter(status=status)
    return render(request, 'orders/manage_list.html', {
        'orders'  : orders,
        'statuses': Order.Status.choices,
        'current' : status,
    })


@role_required(User.Role.OPERATOR, User.Role.ADMIN)
def manage_detail(request, pk):
    order = get_object_or_404(
        Order.objects.select_related('user').prefetch_related('items__product', 'payments'),
        pk=pk
    )
    form = OrderStatusForm(request.POST or None, initial={'status': order.status})
    if request.method == 'POST' and form.is_valid():
        order.status = form.cleaned_data['status']
        order.save(update_fields=['status'])
        messages.success(request, f'Estado de la orden #{order.pk} actualizado.')
        return redirect('orders:manage_detail', pk=order.pk)
    return render(request, 'orders/manage_detail.html', {'order': order, 'form': form})
