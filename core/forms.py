from django import forms
from django.core.validators import FileExtensionValidator
from .models import TempUpload

class Upload(forms.Form):
    file = forms.FileField(
        required = True,
        validators = [
            FileExtensionValidator(
                allowed_extensions = ['zip', 'tar', 'gz', '7z', 'rar', 'bz2', 'xz']
            )
        ]
    )

    class Meta:
        model = TempUpload
        fields = ['file']

class PasswordForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, required=True)
