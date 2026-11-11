from django.contrib                 import messages
from django.contrib.auth.decorators import login_required
from django.conf                    import settings
from django.http                    import FileResponse, Http404, HttpResponse
from django.shortcuts               import get_object_or_404, redirect, render

from apps.orders.models import Order
from apps.services.crypto import signing
from .forms    import ReceiptVerificationForm, SimulatedPaymentForm
from .models   import PaymentReceipt
from .services import PaymentNotAllowedError, process_simulated_payment


@login_required
def pay_order(request, order_id):
    order = get_object_or_404(Order.objects.prefetch_related('items__product'), pk=order_id, user=request.user)
    if not order.can_be_paid:
        messages.info(request, 'Esta orden ya no admite pagos.')
        return redirect('orders:detail', pk=order.pk)

    form = SimulatedPaymentForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        try:
            payment = process_simulated_payment(order, approve=form.cleaned_data['result'] == 'approved')
        except PaymentNotAllowedError as exc:
            messages.error(request, str(exc))
            return redirect('orders:detail', pk=order.pk)

        if payment.status == payment.Status.COMPLETED:
            messages.success(request, f'Pago aprobado. Referencia {payment.transaction_reference}.')
            return redirect('orders:detail', pk=order.pk)
        messages.error(request, f'Pago rechazado. Referencia {payment.transaction_reference}. Puedes reintentar.')
        return redirect('payments:pay', order_id=order.pk)

    return render(request, 'payments/pay.html', {'order': order, 'form': form})


@login_required
def receipt_list(request):
    receipts = PaymentReceipt.objects.filter(
        payment__order__user=request.user
    ).select_related('payment__order')
    return render(request, 'payments/receipts.html', {'receipts': receipts})


@login_required
def receipt_detail(request, pk):
    receipt = get_object_or_404(
        PaymentReceipt.objects.select_related('payment__order'),
        pk=pk, payment__order__user=request.user
    )
    return render(request, 'payments/receipt_detail.html', {
        'receipt': receipt,
        'content': receipt.read_text(),
    })


@login_required
def receipt_download(request, pk):
    receipt = get_object_or_404(PaymentReceipt, pk=pk, payment__order__user=request.user)
    return FileResponse(
        receipt.receipt_file.open('rb'),
        as_attachment = True,
        filename      = f'comprobante_{receipt.pk}.txt',
        content_type  = 'text/plain; charset=utf-8'
    )


@login_required
def receipt_signature(request, pk):
    receipt = get_object_or_404(PaymentReceipt, pk=pk, payment__order__user=request.user)
    response = HttpResponse(receipt.signature, content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="comprobante_{receipt.pk}.sig"'
    return response


@login_required
def receipt_verify(request):
    form   = ReceiptVerificationForm(request.POST or None, request.FILES or None)
    result = None
    if request.method == 'POST' and form.is_valid():
        content = form.cleaned_data['receipt_file'].read()
        result  = signing.verify(content, form.cleaned_data['signature'])
    return render(request, 'payments/verify.html', {'form': form, 'result': result})


def public_key(request):
    try:
        key_file = open(settings.SIGNING_PUBLIC_KEY_PATH, 'rb')
    except OSError:
        raise Http404('Clave publica no disponible.')
    return FileResponse(
        key_file,
        as_attachment = True,
        filename      = 'clave_publica_comprobantes.pem',
        content_type  = 'application/x-pem-file'
    )