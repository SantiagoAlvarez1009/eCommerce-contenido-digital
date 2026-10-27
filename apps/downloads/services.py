import secrets

from django.db import transaction
from django.db.models import F

from apps.orders.services import purchase_order_for
from . import fingerprinting
from .models import Download, FingerPrint


class NotPurchasedError(Exception):
    """The user has not acquired the product."""


def new_fingerprint_value():
    return f'FP-{secrets.token_hex(12).upper()}'


def get_or_create_fingerprint(user, order, product):
    """One fingerprint per (user, order, product): repeated downloads carry the same one."""
    existing = FingerPrint.objects.filter(user=user, order=order, product=product).first()
    if existing:
        return existing
    return FingerPrint.objects.create(
        user        = user,
        order       = order,
        product     = product,
        fingerprint = new_fingerprint_value()
    )


@transaction.atomic
def prepare_download(user, product):
    """
    Build the personalized copy of a product for a user who has bought it.
    Returns (content_bytes, file_name, fingerprint).
    """
    order = purchase_order_for(user, product)
    if order is None:
        raise NotPurchasedError('El producto no ha sido adquirido por este usuario.')

    fp = get_or_create_fingerprint(user, order, product)
    with product.file_path.open('rb') as f:
        content = fingerprinting.embed(f.read(), fp.fingerprint)

    download, created = Download.objects.get_or_create(
        user = user, product = product, defaults={'download_count': 1}
    )
    if not created:
        Download.objects.filter(pk=download.pk).update(download_count=F('download_count') + 1)
        download.save(update_fields=['last_downloaded_at'])

    return content, product.file_name or product.file_path.name, fp


def identify_content(data):
    """Recover the FingerPrint record (user, order, product) from a suspicious copy."""
    value = fingerprinting.extract(data)
    if value is None:
        return None
    return FingerPrint.objects.select_related('user', 'order', 'product').filter(fingerprint=value).first()
