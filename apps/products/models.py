import hashlib
import os

from django.db import models


class DigitalProduct(models.Model):
    class Status(models.TextChoices):
        PURCHASED     = 'comprado'      , 'Comprado'
        AVAILABLE     = 'disponible'    , 'Disponible'
        NOT_AVAILABLE = 'no_disponible' , 'No disponible'

    name = models.CharField(
        max_length = 255
    )
    description = models.CharField(
        max_length = 400
    )
    price = models.DecimalField(
        max_digits     = 10,
        decimal_places = 2
    )
    file_name = models.CharField(
        max_length = 255,
        blank      = True
    )
    file_path = models.FileField(
        upload_to = 'digital_products/'
    )
    file_hash = models.CharField(
        max_length = 64,
        blank      = True,
        null       = True
    )
    quantity = models.PositiveIntegerField(
        default = 1
    )
    status = models.CharField(
        max_length = 20,
        choices    = Status.choices,
        default    = Status.AVAILABLE
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_available(self):
        return self.status == self.Status.AVAILABLE

    def save(self, *args, **kwargs):
        if self.file_path:
            if not self.file_path._committed:
                # Newly uploaded file, not yet in storage until super().save().
                self.file_name = os.path.basename(self.file_path.name)
                self.file_hash = self.compute_hash(self.file_path.file)
            elif not self.file_hash:
                # File already stored (e.g. saved via FieldFile.save) without a hash.
                self.file_name = self.file_name or os.path.basename(self.file_path.name)
                self.file_hash = self.current_file_hash()
        super().save(*args, **kwargs)

    @staticmethod
    def compute_hash(file_obj):
        """SHA-256 of a file-like object, read in chunks."""
        sha256 = hashlib.sha256()
        file_obj.seek(0)
        for chunk in iter(lambda: file_obj.read(64 * 1024), b''):
            sha256.update(chunk)
        file_obj.seek(0)
        return sha256.hexdigest()

    def current_file_hash(self):
        """SHA-256 of the file currently in storage."""
        with self.file_path.open('rb') as f:
            return self.compute_hash(f)

    def file_is_intact(self):
        return bool(self.file_hash) and self.current_file_hash() == self.file_hash
