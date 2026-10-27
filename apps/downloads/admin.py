from django.contrib import admin

from .models import Download, FingerPrint


@admin.register(Download)
class DownloadAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'download_count', 'last_downloaded_at')


@admin.register(FingerPrint)
class FingerPrintAdmin(admin.ModelAdmin):
    list_display  = ('fingerprint', 'user', 'order', 'product', 'created_at')
    search_fields = ('fingerprint', 'user__email')
