# Generated by Django 5.2.1 on 2025-05-29 12:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_alter_csvresult_comment_alter_csvresult_csv_file_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='csvresult',
            name='analysis',
            field=models.JSONField(blank=True, null=True, verbose_name='Analiza'),
        ),
    ]
