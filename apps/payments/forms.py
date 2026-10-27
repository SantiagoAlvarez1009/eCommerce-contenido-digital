from django import forms


class SimulatedPaymentForm(forms.Form):
    """Only chooses the simulated outcome; no card or bank data is collected."""
    result = forms.ChoiceField(
        label   = 'Resultado de la simulacion',
        choices = [
            ('approved', 'Pago aprobado'),
            ('failed'  , 'Pago rechazado'),
        ],
        initial = 'approved',
        widget  = forms.RadioSelect
    )
