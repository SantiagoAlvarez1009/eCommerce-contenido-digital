from django.urls import path

from . import views

app_name = 'downloads'

urlpatterns = [
    path(''                     , views.library          , name='library'),
    path('<int:product_id>/'    , views.download_product , name='download'),
]
