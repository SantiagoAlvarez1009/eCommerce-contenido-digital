from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch             import receiver

from .services import Event, Result, log_event


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    log_event(Event.LOGIN_SUCCESS, request, user=user)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    log_event(Event.LOGOUT, request, user=user)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    log_event(
        Event.LOGIN_FAILED,
        request,
        result = Result.FAILURE,
        email  = str(credentials.get('username', '')),
    )
