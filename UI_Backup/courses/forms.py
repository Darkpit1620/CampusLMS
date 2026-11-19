
from django import forms
from .models import CourseMaterial


class CourseMaterialForm(forms.ModelForm):
    class Meta:
        model = CourseMaterial

        fields = [
            "title",
            "description",
            "file",
        ]

        widgets = {
            "title": forms.TextInput(attrs={
                "placeholder": "Enter material title"
            }),
            "description": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe this material"
            }),
        }
