from django import forms

from .models import DigitalProduct


class ProductForm(forms.ModelForm):
    class Meta:
        model   = DigitalProduct
        fields  = ('name', 'description', 'price', 'file_path', 'status')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'maxlength': 400}),
        }
        labels = {
            'file_path': 'Archivo',
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError('El precio no puede ser negativo.')
        return price
