from django import forms

from .models import Order


class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(label='Nuevo estado')

    def __init__(self, *args, order, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['status'].choices = [
            (status, Order.Status(status).label) for status in order.allowed_transitions
        ]
