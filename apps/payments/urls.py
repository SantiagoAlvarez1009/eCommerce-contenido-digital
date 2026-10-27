from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('pagar/<int:order_id>/'           , views.pay_order        , name='pay'),
    path('comprobantes/'                   , views.receipt_list     , name='receipts'),
    path('comprobantes/<int:pk>/'          , views.receipt_detail   , name='receipt_detail'),
    path('comprobantes/<int:pk>/descargar/', views.receipt_download , name='receipt_download'),
]
