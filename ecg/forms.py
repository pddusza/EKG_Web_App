from django import forms
from .models import ECGSignal

class UploadECGForm(forms.ModelForm):
    sampling_rate = forms.IntegerField(label="Częstotliwość próbkowania (Hz)", min_value=1, initial=100, required=False, 
                                       help_text="Pozostaw puste, aby użyć domyślnego 100 Hz." )

    class Meta:
        model  = ECGSignal
        fields = ['file', 'sampling_rate']