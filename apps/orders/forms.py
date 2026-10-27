from django import forms

from .models import Order


class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Order.Status.choices, label='Estado')
