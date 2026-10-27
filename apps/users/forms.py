from django import forms
from django.contrib.auth.forms import BaseUserCreationForm

from .models import User


class RegisterForm(BaseUserCreationForm):
    class Meta:
        model  = User
        fields = ('email', 'name')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email


class ProfileForm(forms.ModelForm):
    class Meta:
        model  = User
        fields = ('name', 'email')

    def clean_email(self):
        email = self.cleaned_data['email'].lower()
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Ya existe una cuenta con este correo.')
        return email


class RoleForm(forms.Form):
    role = forms.ChoiceField(choices=User.Role.choices)
