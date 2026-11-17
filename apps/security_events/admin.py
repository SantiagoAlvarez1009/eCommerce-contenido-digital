from django.contrib import admin

from .models import SecurityEvent


@admin.register(SecurityEvent)
class SecurityEventAdmin(admin.ModelAdmin):
    list_display  = ('created_at', 'event', 'result', 'email', 'origin', 'details')
    list_filter   = ('event', 'result')
    search_fields = ('email', 'details', 'origin')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
