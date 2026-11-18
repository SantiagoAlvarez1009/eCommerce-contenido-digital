from django.urls import path

from . import views

app_name = 'security_events'

urlpatterns = [
    path('', views.event_list, name='list'),
]
