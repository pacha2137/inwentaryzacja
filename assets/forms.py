from django import forms
from .models import Asset

class Asset_form(forms.ModelForm):
    class Meta:
        model=Asset
        fields = [
            'tag',
            'category',
            'manufacturer',
            'model',
            'serial_number',
            'assigned_to',
        ]
