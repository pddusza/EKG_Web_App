from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import CSVResult, Profile
from datetime import date


# List of bundled static icons here (filenames under static/avatars/)
ICON_CHOICES = [
    ('icon1.jpg', 'Ikona 1'),
    ('icon2.jpg', 'Ikona 2'),
    ('icon3.jpg', 'Ikona 3'),
    ('icon4.jpg', 'Ikona 4'),
]


class CustomUserCreationForm(UserCreationForm):
    email           = forms.EmailField(required=True)
    first_name      = forms.CharField(required=False)
    last_name       = forms.CharField(required=False)

    # patient-only
    pesel           = forms.CharField(required=False)
    birth_date      = forms.DateField(
                         required=False,
                         widget=forms.DateInput(attrs={'type': 'date'})
                     )
    medical_history = forms.CharField(
                         required=False,
                         widget=forms.Textarea(attrs={'rows': 3})
                     )

    # doctor-only
    license_number  = forms.CharField(required=False)
    bio             = forms.CharField(
                         required=False,
                         widget=forms.Textarea(attrs={'rows': 3})
                     )

    # avatar fields
    avatar_upload   = forms.ImageField(
                         required=False,
                         help_text="Plik max. 1 MB"
                     )
    avatar_choice   = forms.ChoiceField(
                         required=False,
                         choices=[('', '— Wybierz ikonę —')] + ICON_CHOICES,
                         widget=forms.RadioSelect
                     )

    class Meta:
        model  = User
        fields = [
            'username','email','password1','password2',
            'first_name','last_name',
            'pesel','birth_date','medical_history',
            'license_number','bio',
            'avatar_upload','avatar_choice',
        ]

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

    def clean_avatar_upload(self):
        img = self.cleaned_data.get('avatar_upload')
        if img and img.size > 1024 * 1024:
            raise forms.ValidationError("Plik jest za duży (maks. 1 MB).")
        return img


class ProfileForm(forms.ModelForm):
    # Include User fields with validation
    username      = forms.CharField(max_length=150, required=True)
    email         = forms.EmailField(required=True)

    # File upload for new avatar
    avatar_upload = forms.ImageField(
        required=False,
        label="Nowy avatar",
        help_text="Plik max 1 MB"
    )

    # Hidden crop data
    offsetX = forms.IntegerField(widget=forms.HiddenInput())
    offsetY = forms.IntegerField(widget=forms.HiddenInput())
    scale   = forms.FloatField(widget=forms.HiddenInput())

    class Meta:
        model  = Profile
        fields = ['first_name', 'last_name', 'bio']

    def clean_username(self):
        uname = self.cleaned_data['username']
        if User.objects.exclude(pk=self.instance.user.pk).filter(username=uname).exists():
            raise forms.ValidationError("Ta nazwa użytkownika jest już zajęta.")
        return uname

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.exclude(pk=self.instance.user.pk).filter(email=email).exists():
            raise forms.ValidationError("Ten email jest już zarejestrowany.")
        return email

    def clean_avatar_upload(self):
        img = self.cleaned_data.get('avatar_upload')
        if img and img.size > 1024*1024:
            raise forms.ValidationError("Plik jest za duży (maks. 1 MB).")
        return img

class CSVResultForm(forms.ModelForm):
    pesel = forms.CharField(
        label="Numer PESEL",
        max_length=11,
        widget=forms.TextInput(attrs={'placeholder': 'Wpisz numer PESEL'})
    )
    exam_date = forms.DateField(
        label="Data wykonania badania",
        initial=date(2000, 1, 1),
        widget=forms.DateInput(attrs={'type':'date'})
    )
    sampling_rate = forms.IntegerField(
        label="Częstotliwość próbki (Hz)",
        min_value=1,
        initial= 100,
        widget=forms.NumberInput(attrs={'placeholder': '[Hz]'})
    )

    class Meta:
        model  = CSVResult
        fields = [
            'title',
            'pesel',
            'csv_file',
            'exam_date',
            'sampling_rate',
            'comment',
        ]
        labels = {
            'title': 'Nazwa wyniku',
            'csv_file': 'Plik CSV',
            'comment': 'Komentarz (opcjonalnie)',
        }
