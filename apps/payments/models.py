from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING    = 'pendiente'  , 'Pendiente'
        PROCESSING = 'procesando' , 'Procesando'
        COMPLETED  = 'completado' , 'Completado'
        FAILED     = 'fallido'    , 'Fallido'

    order = models.ForeignKey(
        'orders.Order',
        on_delete    = models.CASCADE,
        related_name = 'payments'
    )
    amount = models.DecimalField(
        max_digits     = 10,
        decimal_places = 2
    )
    status = models.CharField(
        max_length = 20,
        choices    = Status.choices,
        default    = Status.PENDING
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    transaction_reference = models.CharField(
        max_length = 255,
        blank      = True,
        null       = True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Payment #{self.pk} - {self.transaction_reference}'


class PaymentReceipt(models.Model):
    payment = models.ForeignKey(
        Payment,
        on_delete    = models.CASCADE,
        related_name = 'receipts'
    )
    receipt_file = models.FileField(
        upload_to = 'payment_receipts/'
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Receipt #{self.pk} - payment {self.payment_id}'

    def read_text(self):
        with self.receipt_file.open('rb') as f:
            return f.read().decode('utf-8')
