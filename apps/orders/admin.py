from django.contrib import admin

from .models import Order, OrderProducts


class OrderProductsInline(admin.TabularInline):
    model = OrderProducts
    extra = 0


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'total', 'status', 'created_at')
    list_filter  = ('status',)
    inlines      = [OrderProductsInline]
