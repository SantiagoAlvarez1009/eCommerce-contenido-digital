from django.contrib.auth import views as auth_views
from django.urls         import path, reverse_lazy

from . import views

app_name = 'users'

urlpatterns = [
    path('registro/' , views.register, name='register'),
    path('login/'    , auth_views.LoginView.as_view(template_name='users/login.html'), name='login'),
    path('logout/'   , auth_views.LogoutView.as_view(), name='logout'),
    path('perfil/'   , views.profile , name='profile'),

    # Password recovery (token sent by email, single use, with expiration)
    path('recuperar/',
         auth_views.PasswordResetView.as_view(
             template_name       = 'registration/password_reset_form.html',
             email_template_name = 'registration/password_reset_email.txt',
             subject_template_name = 'registration/password_reset_subject.txt',
             success_url         = reverse_lazy('users:password_reset_done')),
         name='password_reset'),
    path('recuperar/enviado/',
         auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'),
         name='password_reset_done'),
    path('recuperar/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name = 'registration/password_reset_confirm.html',
             success_url   = reverse_lazy('users:password_reset_complete')),
         name='password_reset_confirm'),
    path('recuperar/completo/',
         auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'),
         name='password_reset_complete'),

    # Administration
    path('gestion/usuarios/'                , views.user_list         , name='manage_list'),
    path('gestion/usuarios/<int:pk>/activar/', views.user_toggle_active, name='manage_toggle'),
    path('gestion/usuarios/<int:pk>/rol/'    , views.user_change_role  , name='manage_role'),
]
