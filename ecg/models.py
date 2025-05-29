from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ECGSignal(models.Model):
    owner       = models.ForeignKey(User, on_delete=models.CASCADE)
    file        = models.FileField(upload_to='ecg_signals/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"ECG #{self.pk} by {self.owner.username} at {self.uploaded_at:%Y-%m-%d %H:%M}"


class AnalysisResult(models.Model):
    signal     = models.OneToOneField(ECGSignal, on_delete=models.CASCADE)
    result_json = models.JSONField()
    created_at  = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Result for ECG #{self.signal.pk}"
