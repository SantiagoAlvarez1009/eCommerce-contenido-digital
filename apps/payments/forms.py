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


MAX_RECEIPT_SIZE   = 64 * 1024
MAX_SIGNATURE_SIZE = 1024


class ReceiptVerificationForm(forms.Form):
    receipt_file = forms.FileField(
        label = 'Comprobante (.txt)'
    )
    signature_file = forms.FileField(
        label    = 'Firma (.sig)',
        required = False
    )
    signature_text = forms.CharField(
        label    = 'O pega la firma',
        required = False,
        widget   = forms.Textarea(attrs={'rows': 3})
    )

    def clean_receipt_file(self):
        receipt_file = self.cleaned_data['receipt_file']
        if receipt_file.size > MAX_RECEIPT_SIZE:
            raise forms.ValidationError('El comprobante es demasiado grande.')
        return receipt_file

    def clean(self):
        cleaned   = super().clean()
        sig_file  = cleaned.get('signature_file')
        signature = (cleaned.get('signature_text') or '').strip()

        if sig_file:
            if sig_file.size > MAX_SIGNATURE_SIZE:
                raise forms.ValidationError('El archivo de firma es demasiado grande.')
            signature = sig_file.read().decode('ascii', errors='ignore').strip()

        if not signature:
            raise forms.ValidationError('Sube el archivo .sig o pega la firma.')

        cleaned['signature'] = signature
        return cleaned