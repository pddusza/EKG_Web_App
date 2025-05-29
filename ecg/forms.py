from django import forms
from .models import ECGSignal

class UploadECGForm(forms.ModelForm):
    class Meta:
        model  = ECGSignal
        fields = ['file']