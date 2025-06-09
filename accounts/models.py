from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from datetime import date

class Profile(models.Model):
    user             = models.OneToOneField(User, on_delete=models.CASCADE)
    avatar           = models.ImageField(
                        upload_to='avatars/avatars_users/',
                        default='avatars/default.png',
                        blank=True
                    )
    first_name       = models.CharField(max_length=30, blank=True)
    last_name        = models.CharField(max_length=30, blank=True)

    # ← extra fields
    pesel            = models.CharField(max_length=11, blank=True, null=True)
    birth_date       = models.DateField(blank=True, null=True)
    medical_history  = models.TextField(blank=True)
    license_number   = models.CharField(max_length=30, blank=True)
    bio              = models.TextField(blank=True)

    # ← privilege flags
    is_patient       = models.BooleanField(default=True)
    is_doctor        = models.BooleanField(default=False)
    is_admin         = models.BooleanField(default=False)

    # ← link each patient to their doctor/doctors
    doctors    = models.ManyToManyField(settings.AUTH_USER_MODEL, blank=True, related_name='patients')
    
    def __str__(self):
        return f"{self.user.username} Profile"

@receiver(post_save, sender=User)
def create_or_update_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)
    else:
        instance.profile.save()


class CSVResult(models.Model):
    owner          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title          = models.CharField("Tytuł", max_length=200)
    # ← questionnaire fields
    pesel          = models.CharField("Numer PESEL", max_length=11, default="")
    csv_file       = models.FileField("Plik CSV", upload_to='csv_results/')
    exam_date      = models.DateField("Data wykonania badania", default=date(2000, 1, 1))
    sampling_rate  = models.PositiveIntegerField("Częstotliwość próbki (Hz)",default=100)
    comment        = models.TextField("Komentarz", blank=True)
    uploaded_at    = models.DateTimeField("Data wysłania", auto_now_add=True)
    analysis       = models.JSONField("Analiza", null=True, blank=True)

    def __str__(self):
        return f"{self.title} ({self.pesel})"