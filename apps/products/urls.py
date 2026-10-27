from django.urls import path

from . import views

app_name = 'products'

urlpatterns = [
    path('gestion/productos/'                , views.product_list  , name='list'),
    path('gestion/productos/nuevo/'          , views.product_create, name='create'),
    path('gestion/productos/<int:pk>/editar/', views.product_edit  , name='edit'),
    path('gestion/productos/<int:pk>/activar/', views.product_toggle, name='toggle'),
]
