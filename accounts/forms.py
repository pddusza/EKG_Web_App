from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CSVResult

class CustomUserCreationForm(UserCreationForm):
    email            = forms.EmailField(required=True)
    first_name       = forms.CharField(required=False)
    last_name        = forms.CharField(required=False)

    # patient‐only
    pesel            = forms.CharField(required=False)
    birth_date       = forms.DateField(
                         required=False,
                         widget=forms.DateInput(attrs={'type': 'date'})
                       )
    medical_history  = forms.CharField(
                         required=False,
                         widget=forms.Textarea(attrs={'rows':3})
                       )

    # doctor‐only
    license_number   = forms.CharField(required=False)
    bio              = forms.CharField(
                         required=False,
                         widget=forms.Textarea(attrs={'rows':3})
                       )

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Ten email jest już zarejestrowany.")
        return email

    def clean_pesel(self):
        pesel = self.cleaned_data.get('pesel', '')
        if pesel and (not pesel.isdigit() or len(pesel) != 11):
            raise forms.ValidationError("Numer PESEL musi składać się z 11 cyfr.")
        return pesel

    class Meta:
        model  = User
        fields = [
          'username','email','first_name','last_name',
          'password1','password2',
          'pesel','birth_date','medical_history',
          'license_number','bio',
        ]



class CSVResultForm(forms.ModelForm):
    class Meta:
        model = CSVResult
        fields = ['title', 'csv_file', 'comment']
        labels = {
            'title': 'Tytuł',
            'csv_file': 'Plik CSV',
            'comment': 'Komentarz (opcjonalnie)',
        }
