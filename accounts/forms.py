from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CSVResult

class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, label="Email")

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


class CSVResultForm(forms.ModelForm):
    class Meta:
        model = CSVResult
        fields = ['title', 'csv_file', 'comment']
        labels = {
            'title': 'Tytuł',
            'csv_file': 'Plik CSV',
            'comment': 'Komentarz (opcjonalnie)',
        }
