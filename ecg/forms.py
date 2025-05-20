from django import forms

class UploadECGForm(forms.Form):
    file = forms.FileField(label="Select your ECG file")
