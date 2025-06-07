# accounts/admin.py

from django.contrib import admin
from .models import Profile

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display  = ('user', 'is_patient', 'is_doctor', 'is_admin')
    list_editable = ('is_patient', 'is_doctor', 'is_admin')
