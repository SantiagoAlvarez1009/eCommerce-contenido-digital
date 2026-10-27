from django.db import models


class Download(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete    = models.CASCADE,
        related_name = 'downloads'
    )
    product = models.ForeignKey(
        'products.DigitalProduct',
        on_delete = models.CASCADE
    )
    download_count = models.PositiveIntegerField(
        default = 0
    )
    last_downloaded_at = models.DateTimeField(
        auto_now = True
    )

    class Meta:
        unique_together = ('user', 'product')

    def __str__(self):
        return f'{self.user} - {self.product} ({self.download_count})'


class FingerPrint(models.Model):
    user = models.ForeignKey(
        'users.User',
        on_delete = models.CASCADE
    )
    product = models.ForeignKey(
        'products.DigitalProduct',
        on_delete = models.CASCADE
    )
    order = models.ForeignKey(
        'orders.Order',
        on_delete = models.CASCADE
    )
    fingerprint = models.CharField(
        max_length = 255,
        unique     = True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ('user', 'product', 'order')

    def __str__(self):
        return self.fingerprint
