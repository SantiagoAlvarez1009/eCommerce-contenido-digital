import os
from io import BytesIO

from django import forms
from django.core.files.uploadedfile import UploadedFile
from PIL   import Image
from pypdf import PdfReader

from apps.downloads.fingerprinting import detect_format
from .models import DigitalProduct

ALLOWED_EXTENSIONS = {
    '.txt': 'txt',
    '.pdf': 'pdf',
    '.png': 'png',
}
MAX_FILE_SIZE_MB = 10
MAX_FILE_SIZE    = MAX_FILE_SIZE_MB * 1024 * 1024

STATUS_CHOICES = [
    (DigitalProduct.Status.AVAILABLE    , DigitalProduct.Status.AVAILABLE.label),
    (DigitalProduct.Status.NOT_AVAILABLE, DigitalProduct.Status.NOT_AVAILABLE.label),
]

MSG_EXTENSION = 'Solo se permiten archivos .txt, .pdf o .png.'
MSG_SIZE      = f'El archivo no puede pesar más de {MAX_FILE_SIZE_MB} MB.'
MSG_CONTENT   = 'El contenido del archivo no corresponde a su extensión.'
MSG_INVALID   = 'El archivo está dañado o no se puede leer.'
MSG_ENCRYPTED = 'No se permiten PDF cifrados o protegidos con contraseña.'


class ProductForm(forms.ModelForm):
    status = forms.ChoiceField(label='Estado', choices=STATUS_CHOICES)

    class Meta:
        model   = DigitalProduct
        fields  = ('name', 'description', 'price', 'file_path', 'status')
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3, 'maxlength': 400}),
            'file_path'  : forms.ClearableFileInput(attrs={'accept': ','.join(ALLOWED_EXTENSIONS)}),
        }
        labels = {
            'file_path': 'Archivo (.txt, .pdf o .png)',
        }

    def clean_price(self):
        price = self.cleaned_data['price']
        if price < 0:
            raise forms.ValidationError('El precio no puede ser negativo.')
        return price

    def clean_file_path(self):
        file = self.cleaned_data.get('file_path')
        # Only validate new uploads
        if not isinstance(file, UploadedFile):
            return file

        expected = ALLOWED_EXTENSIONS.get(os.path.splitext(file.name)[1].lower())
        if expected is None:
            raise forms.ValidationError(MSG_EXTENSION)
        if file.size > MAX_FILE_SIZE:
            raise forms.ValidationError(MSG_SIZE)

        file.seek(0)
        data = file.read()
        file.seek(0)

        # The content must match the extension
        if detect_format(data) != expected:
            raise forms.ValidationError(MSG_CONTENT)
        if expected == 'pdf':
            self._validate_pdf(data)
        elif expected == 'png':
            self._validate_png(data)
        return file

    @staticmethod
    def _validate_pdf(data):
        try:
            reader = PdfReader(BytesIO(data))
            encrypted = reader.is_encrypted
            if not encrypted and len(reader.pages) == 0:
                raise ValueError('PDF without pages')
        except Exception:
            raise forms.ValidationError(MSG_INVALID)
        if encrypted:
            raise forms.ValidationError(MSG_ENCRYPTED)

    @staticmethod
    def _validate_png(data):
        try:
            Image.open(BytesIO(data)).verify()
        except Exception:
            raise forms.ValidationError(MSG_INVALID)