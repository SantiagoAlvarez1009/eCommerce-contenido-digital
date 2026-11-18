from django.apps import AppConfig


class SecurityEventsConfig(AppConfig):
    name = 'apps.security_events'

    def ready(self):
        from . import signals
