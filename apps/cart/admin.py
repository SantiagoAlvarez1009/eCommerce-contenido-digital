from django.contrib import admin

from .models import Cart, CartProducts


class CartProductsInline(admin.TabularInline):
    model = CartProducts
    extra = 0


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'created_at')
    inlines      = [CartProductsInline]
