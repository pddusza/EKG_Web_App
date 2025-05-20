from django.db import models
from accounts.models import UserProfile

class ECGSignal(models.Model):
    owner = models.ForeignKey(UserProfile, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='ecg/')

class AnalysisResult(models.Model):
    signal = models.ForeignKey(ECGSignal, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    result_json = models.JSONField()
