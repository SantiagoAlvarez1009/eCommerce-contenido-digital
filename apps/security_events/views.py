from django.core.paginator import Paginator
from django.shortcuts      import render

from apps.services.permissions.roles import role_required
from apps.users.models               import User
from .models import SecurityEvent


@role_required(User.Role.ADMIN)
def event_list(request):
    events = SecurityEvent.objects.all()

    event  = request.GET.get('evento', '')
    result = request.GET.get('resultado', '')
    email  = request.GET.get('correo', '').strip()[:254]

    if event in SecurityEvent.Event.values:
        events = events.filter(event=event)
    else:
        event = ''
    if result in SecurityEvent.Result.values:
        events = events.filter(result=result)
    else:
        result = ''
    if email:
        events = events.filter(email__icontains=email)

    page = Paginator(events, 50).get_page(request.GET.get('pagina'))
    return render(request, 'security_events/list.html', {
        'page'    : page,
        'events'  : SecurityEvent.Event.choices,
        'results' : SecurityEvent.Result.choices,
        'current' : {'evento': event, 'resultado': result, 'correo': email},
    })
