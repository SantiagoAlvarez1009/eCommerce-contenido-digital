from django.conf import settings
from django.db   import models


class SecurityEvent(models.Model):
    class Event(models.TextChoices):
        LOGIN_SUCCESS       = 'LOGIN_SUCCESS'      , 'Inicio de sesión'
        LOGIN_FAILED        = 'LOGIN_FAILED'       , 'Inicio de sesión fallido'
        LOGOUT              = 'LOGOUT'             , 'Cierre de sesión'
        PASSWORD_RESET      = 'PASSWORD_RESET'     , 'Restablecimiento de contraseña'
        ORDER_CREATED       = 'ORDER_CREATED'      , 'Orden creada'
        ORDER_STATUS_CHANGED = 'ORDER_STATUS_CHANGED', 'Cambio de estado de orden'
        PAYMENT_APPROVED    = 'PAYMENT_APPROVED'   , 'Pago aprobado'
        DOWNLOAD            = 'DOWNLOAD'           , 'Descarga'
        ROLE_CHANGED        = 'ROLE_CHANGED'       , 'Cambio de rol'
        ACCOUNT_DISABLED    = 'ACCOUNT_DISABLED'   , 'Cuenta desactivada'
        ACCOUNT_ENABLED     = 'ACCOUNT_ENABLED'    , 'Cuenta activada'
        SESSION_REVOKED     = 'SESSION_REVOKED'    , 'Sesiones revocadas'
        SIGNATURE_CREATED   = 'SIGNATURE_CREATED'  , 'Firma creada'
        FINGERPRINT_CREATED = 'FINGERPRINT_CREATED', 'Fingerprint creado'

    class Result(models.TextChoices):
        SUCCESS = 'exito', 'Éxito'
        FAILURE = 'fallo', 'Fallo'

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete    = models.SET_NULL,
        null         = True,
        blank        = True,
        related_name = 'security_events'
    )
    email = models.EmailField(
        blank = True
    )
    event = models.CharField(
        max_length = 32,
        choices    = Event.choices
    )
    result = models.CharField(
        max_length = 10,
        choices    = Result.choices,
        default    = Result.SUCCESS
    )
    origin = models.GenericIPAddressField(
        null  = True,
        blank = True
    )
    details = models.CharField(
        max_length = 255,
        blank      = True
    )
    created_at = models.DateTimeField(
        auto_now_add = True,
        db_index     = True
    )

    class Meta:
        db_table = 'security_events'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.created_at:%Y-%m-%d %H:%M:%S} {self.event} {self.email or "-"}'

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValueError('Los eventos de seguridad no se pueden modificar.')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Los eventos de seguridad no se pueden eliminar.')
