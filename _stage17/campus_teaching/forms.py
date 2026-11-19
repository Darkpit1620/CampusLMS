from pathlib import Path
from django import forms
from django.db import models
from django.forms import modelform_factory
from assignments.models import Assignment
from courses.models import CourseMaterial


MATERIAL_EXTENSIONS = {'.pdf', '.docx', '.pptx', '.xlsx', '.txt', '.odt', '.ods', '.odp'}
MAX_MATERIAL_BYTES = 20 * 1024 * 1024


def material_form():
    names = {f.name for f in CourseMaterial._meta.fields}
    file_names = [f.name for f in CourseMaterial._meta.fields if isinstance(f, models.FileField)]
    if not file_names:
        raise ValueError('CourseMaterial must include a file upload field.')
    allowed = [f for f in ['title', 'description'] if f in names]
    file_name = file_names[0]
    allowed.append(file_name)
    factory = modelform_factory(CourseMaterial, fields=allowed)

    class SafeMaterialForm(factory):
        def clean(self):
            result = super().clean()
            uploaded = result.get(file_name)
            if uploaded:
                if Path(uploaded.name).suffix.lower() not in MATERIAL_EXTENSIONS:
                    self.add_error(file_name, 'Upload a PDF, Office document or TXT file.')
                if uploaded.size > MAX_MATERIAL_BYTES:
                    self.add_error(file_name, 'Maximum upload size is 20 MB.')
            return result

    return SafeMaterialForm


def assignment_form():
    names = {f.name for f in Assignment._meta.fields}
    allowed = [f for f in ('title', 'instructions', 'description', 'deadline', 'due_date', 'max_marks') if f in names]
    if not 'title' in allowed:
        raise ValueError('The Assignment model needs a title field.')
    widgets = {}
    for name in ('deadline', 'due_date'):
        if name in allowed:
            widgets[name] = forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M')
    return modelform_factory(Assignment, fields=allowed, widgets=widgets)
