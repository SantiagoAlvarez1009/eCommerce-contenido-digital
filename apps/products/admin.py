from django.contrib import admin

from .models import DigitalProduct


@admin.register(DigitalProduct)
class DigitalProductAdmin(admin.ModelAdmin):
    list_display    = ('name', 'price', 'status', 'file_name', 'created_at')
    list_filter     = ('status',)
    search_fields   = ('name', 'description')
    readonly_fields = ('file_name', 'file_hash', 'created_at')
