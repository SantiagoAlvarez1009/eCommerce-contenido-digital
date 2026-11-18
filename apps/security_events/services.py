import ipaddress

from django.conf import settings

from .models import SecurityEvent

Event  = SecurityEvent.Event
Result = SecurityEvent.Result


def valid_ip(value):
    try:
        return str(ipaddress.ip_address((value or '').strip()))
    except ValueError:
        return None


def client_ip(request):
    if request is None:
        return None
    if getattr(settings, 'SECURITY_EVENTS_TRUST_X_REAL_IP', False):
        forwarded = valid_ip(request.META.get('HTTP_X_REAL_IP'))
        if forwarded:
            return forwarded
    return valid_ip(request.META.get('REMOTE_ADDR'))


def log_event(event, request=None, user=None, result=Result.SUCCESS, details='', email=''):
    if user is None and request is not None:
        current = getattr(request, 'user', None)
        if current is not None and current.is_authenticated:
            user = current
    if not email and user is not None:
        email = user.email
    return SecurityEvent.objects.create(
        user    = user,
        email   = (email or '')[:254],
        event   = event,
        result  = result,
        origin  = client_ip(request),
        details = (details or '')[:255],
    )
