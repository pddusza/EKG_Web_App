# Generated by Django 5.2.1 on 2025-05-29 09:18

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ecg', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='analysisresult',
            name='signal',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='ecg.ecgsignal'),
        ),
        migrations.AlterField(
            model_name='ecgsignal',
            name='file',
            field=models.FileField(upload_to='ecg_signals/'),
        ),
        migrations.AlterField(
            model_name='ecgsignal',
            name='owner',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]
