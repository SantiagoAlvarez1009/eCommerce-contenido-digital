from .models import SecurityEvent

Event  = SecurityEvent.Event
Result = SecurityEvent.Result


def client_ip(request):
    if request is None:
        return None
    return request.META.get('REMOTE_ADDR') or None


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
