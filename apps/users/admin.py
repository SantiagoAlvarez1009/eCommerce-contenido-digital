from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    ordering        = ('email',)
    list_display    = ('email', 'name', 'role', 'status', 'is_active', 'created_at')
    list_filter     = ('role', 'status', 'is_active')
    search_fields   = ('email', 'name')
    fieldsets = (
        (None            , {'fields': ('email', 'password')}),
        ('Datos'         , {'fields': ('name', 'first_name', 'last_name')}),
        ('Rol y estado'  , {'fields': ('role', 'status', 'is_active', 'is_staff', 'is_superuser')}),
        ('Permisos'      , {'fields': ('groups', 'user_permissions')}),
        ('Fechas'        , {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields' : ('email', 'name', 'role', 'password1', 'password2'),
        }),
    )
