"""
URL configuration for config project.
"""
from django.conf          import settings
from django.conf.urls.static import static
from django.contrib       import admin
from django.urls          import include, path

urlpatterns = [
    path('admin/'     , admin.site.urls),
    path(''           , include('apps.catalog.urls')),
    path('cuentas/'   , include('apps.users.urls')),
    path(''           , include('apps.products.urls')),
    path('carrito/'   , include('apps.cart.urls')),
    path('ordenes/'   , include('apps.orders.urls')),
    path('pagos/'     , include('apps.payments.urls')),
    path('descargas/' , include('apps.downloads.urls')),
]

# Local development only: serve uploaded media. In production it lives in S3.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
