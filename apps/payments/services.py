import uuid

from django.core.files.base import ContentFile
from django.db              import transaction

from apps.orders.models import Order
from .models            import Payment, PaymentReceipt


class PaymentNotAllowedError(Exception):
    """The order is not in a state that accepts a payment."""


def new_transaction_reference():
    return f'SIM-{uuid.uuid4().hex[:12].upper()}'


def build_receipt_text(payment):
    """Plain-text content of the receipt (order, user, products, total, date, reference)."""
    order = payment.order
    lines = [
        'COMPROBANTE DE COMPRA',
        '=====================',
        f'Orden        : {order.pk}',
        f'Usuario      : {order.user.email}',
        f'Fecha        : {payment.created_at:%Y-%m-%d %H:%M:%S %Z}',
        f'Referencia   : {payment.transaction_reference}',
        '',
        'Productos:',
    ]
    for item in order.items.select_related('product'):
        lines.append(f'  - {item.product.name}  ${item.price}')
    lines += ['', f'Total        : ${payment.amount}', '']
    return '\n'.join(lines)


def create_receipt(payment):
    content = build_receipt_text(payment).encode('utf-8')
    receipt = PaymentReceipt(payment=payment)
    receipt.receipt_file.save(
        f'comprobante_orden_{payment.order_id}_{payment.pk}.txt',
        ContentFile(content),
        save = True
    )
    return receipt


@transaction.atomic
def process_simulated_payment(order, approve):
    """
    Simulate the outcome of a payment. No card or bank data is handled.
    Approved: the order is completed and a receipt is generated.
    Failed: the order stays pending so the user can retry.
    """
    order = Order.objects.select_for_update().get(pk=order.pk)
    if not order.can_be_paid:
        raise PaymentNotAllowedError('Esta orden no admite pagos.')

    payment = Payment.objects.create(
        order                 = order,
        amount                = order.total,
        status                = Payment.Status.COMPLETED if approve else Payment.Status.FAILED,
        transaction_reference = new_transaction_reference()
    )
    if approve:
        order.status = Order.Status.COMPLETED
        order.save(update_fields=['status'])
        create_receipt(payment)
    return payment
