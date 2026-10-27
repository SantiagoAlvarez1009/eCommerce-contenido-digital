from django.urls import path

from . import views

app_name = 'orders'

urlpatterns = [
    path('comprar/'                   , views.checkout     , name='checkout'),
    path('mis-ordenes/'               , views.order_list   , name='list'),
    path('mis-ordenes/<int:pk>/'      , views.order_detail , name='detail'),
    path('mis-ordenes/<int:pk>/cancelar/', views.order_cancel, name='cancel'),

    # Operator
    path('gestion/'                   , views.manage_list  , name='manage_list'),
    path('gestion/<int:pk>/'          , views.manage_detail, name='manage_detail'),
]
