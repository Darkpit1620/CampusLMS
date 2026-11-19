"""New forms wrap existing signup forms, preserving admission and email logic."""
from django import forms
from django.db import transaction
from academics.models import Programme, ProgrammeUnit
from campus_access.forms import EmployeeSignupForm
from campus_admissions_units.forms import ApplicantSignupForm
from .models import LecturerDepartmentPreference, LecturerUnitRequest


def department_choices():
    departments = sorted(set(
        Programme.objects.filter(is_active=True).exclude(department='')
        .values_list('department', flat=True)
    ), key=str.casefold)
    return [('', 'Select your department')] + [(v, v) for v in departments]


def department_units(department):
    return ProgrammeUnit.objects.filter(
        programme__is_active=True, programme__department=department,
    ).select_related('programme', 'unit').order_by(
        'year', 'semester', 'programme__name', 'unit__code',
    )


class DepartmentStudentSignupForm(ApplicantSignupForm):
    department = forms.ChoiceField(label='Department / School', choices=())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].choices = department_choices()
        department = self.data.get('department') if self.is_bound else self.initial.get('department')
        # Server-side validation: a programme from another department is never accepted.
        self.fields['programme'].queryset = (
            Programme.objects.filter(is_active=True, department=department)
            if department else Programme.objects.none()
        )
        order = list(self.fields)
        order.remove('department')
        order.insert(order.index('programme'), 'department')
        self.order_fields(order)

    def clean(self):
        data = super().clean()
        if data.get('programme') and data.get('department') != data['programme'].department:
            self.add_error('programme', 'Choose a programme from your selected department.')
        return data


class UnitSelectionMixin:
    def setup_unit_fields(self):
        self.fields['department'].choices = department_choices()
        department = self.data.get('department') if self.is_bound else self.initial.get('department')
        choices = {k for k, _v in self.fields['department'].choices if k}
        self.fields['requested_units'].queryset = (
            department_units(department) if department in choices else ProgrammeUnit.objects.none()
        )


class DepartmentEmployeeSignupForm(UnitSelectionMixin, EmployeeSignupForm):
    department = forms.ChoiceField(label='Department / School', choices=())
    requested_units = forms.ModelMultipleChoiceField(
        label='Units you would like to teach (all years and semesters)',
        queryset=ProgrammeUnit.objects.none(), required=False,
        help_text='Select units for your department. The administrator must approve your teaching requests.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.requested_role == 'STAFF':
            del self.fields['requested_units']
            self.fields['department'].choices = department_choices()
        else:
            self.setup_unit_fields()
            order = list(self.fields)
            order.remove('requested_units')
            order.insert(order.index('job_title'), 'requested_units')
            self.order_fields(order)

    @transaction.atomic
    def save(self):
        employee_application = super().save()
        if self.requested_role == 'LECTURER':
            LecturerDepartmentPreference.objects.create(
                lecturer=employee_application.user, department=self.cleaned_data['department']
            )
            LecturerUnitRequest.objects.bulk_create([
                LecturerUnitRequest(lecturer=employee_application.user, placement=unit)
                for unit in self.cleaned_data.get('requested_units', [])
            ])
        return employee_application


class LecturerUnitRequestForm(UnitSelectionMixin, forms.Form):
    department = forms.ChoiceField(label='Your Department / School', choices=())
    requested_units = forms.ModelMultipleChoiceField(
        label='Units to request', queryset=ProgrammeUnit.objects.none(),
        required=False,
        help_text='Choose additional units across Year 1–4 and Semesters 1–3. All requests need admin approval.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setup_unit_fields()

    @transaction.atomic
    def save(self, user):
        department = self.cleaned_data['department']
        LecturerDepartmentPreference.objects.update_or_create(
            lecturer=user, defaults={'department': department}
        )
        added = 0
        for unit in self.cleaned_data['requested_units']:
            request, created = LecturerUnitRequest.objects.get_or_create(
                lecturer=user, placement=unit
            )
            if created:
                added += 1
            elif request.status == LecturerUnitRequest.Status.REJECTED:
                request.status = LecturerUnitRequest.Status.PENDING
                request.review_note = ''
                request.reviewed_by = None
                request.reviewed_at = None
                request.save(update_fields=('status', 'review_note', 'reviewed_by', 'reviewed_at'))
                added += 1
        return added
