from django.db            import models
from apps.products.models import DigitalProduct


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING    = 'pendiente'  , 'Pendiente'
        PROCESSING = 'procesando' , 'Procesando'
        COMPLETED  = 'completado' , 'Completado'
        CANCELLED  = 'cancelado'  , 'Cancelado'

    user = models.ForeignKey(
        'users.User',
        on_delete    = models.CASCADE,
        related_name = 'orders'
    )
    products = models.ManyToManyField(
        DigitalProduct,
        through      = 'OrderProducts',
        related_name = 'orders'
    )
    total = models.DecimalField(
        max_digits     = 10,
        decimal_places = 2,
        default        = 0
    )
    status = models.CharField(
        max_length = 20,
        choices    = Status.choices,
        default    = Status.PENDING
    )
    created_at = models.DateTimeField(
        auto_now_add = True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'Order #{self.pk} - {self.user}'

    @property
    def is_paid(self):
        return self.status == self.Status.COMPLETED

    @property
    def can_be_paid(self):
        return self.status in (self.Status.PENDING, self.Status.PROCESSING)


class OrderProducts(models.Model):
    order = models.ForeignKey(
        Order,
        on_delete    = models.CASCADE,
        related_name = 'items'
    )
    product = models.ForeignKey(
        DigitalProduct,
        on_delete = models.PROTECT
    )
    # Price at the moment of purchase, independent from the current product price.
    price = models.DecimalField(
        max_digits     = 10,
        decimal_places = 2
    )

    class Meta:
        unique_together = ('order', 'product')

    def __str__(self):
        return f'{self.order_id} - {self.product_id}'
