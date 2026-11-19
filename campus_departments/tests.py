from decimal import Decimal
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from academics.models import Programme, Unit, ProgrammeUnit
from campus_admissions_units.models import ProgrammeRequirement, UnitLecturerAssignment
from .forms import DepartmentStudentSignupForm, LecturerUnitRequestForm, DepartmentEmployeeSignupForm
from .models import LecturerUnitRequest


class DepartmentSelectionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.computing = Programme.objects.create(code='TEST-CS', name='Test Computing', department='School of Computing')
        cls.business = Programme.objects.create(code='TEST-BA', name='Test Business', department='School of Business')
        a = Unit.objects.create(code='TCS-10', title='Intro to Code')
        b = Unit.objects.create(code='TBA-10', title='Business Introduction')
        c = Unit.objects.create(code='TCS-20', title='Advanced Code')
        cls.cs_slot = ProgrammeUnit.objects.create(programme=cls.computing, unit=a, year=1, semester=1)
        cls.ba_slot = ProgrammeUnit.objects.create(programme=cls.business, unit=b, year=1, semester=1)
        cls.cs_later = ProgrammeUnit.objects.create(programme=cls.computing, unit=c, year=2, semester=3)
        ProgrammeRequirement.objects.create(
            programme=cls.computing, minimum_cluster_points=Decimal('25'), minimum_mean_grade='C+',
        )
        ProgrammeRequirement.objects.create(
            programme=cls.business, minimum_cluster_points=Decimal('20'), minimum_mean_grade='C+',
        )

    def test_student_sees_all_departments(self):
        form = DepartmentStudentSignupForm()
        choices = dict(form.fields['department'].choices)
        self.assertIn('School of Computing', choices)
        self.assertIn('School of Business', choices)
        self.assertEqual(form.fields['programme'].queryset.count(), 0)

    def test_eligibility_endpoint_respects_department(self):
        url = reverse('campus_departments:eligible_programmes')
        response = self.client.get(url, {'department': 'School of Computing', 'grade': 'B', 'points': '30'})
        self.assertEqual(response.status_code, 200)
        ids = [p['id'] for p in response.json()['programmes']]
        self.assertEqual(ids, [self.computing.pk])

    def test_units_endpoint_has_multiple_years_without_other_department(self):
        response = self.client.get(reverse('campus_departments:unit_options'), {'department': 'School of Computing'})
        ids = {u['id'] for u in response.json()['units']}
        self.assertEqual(ids, {self.cs_slot.pk, self.cs_later.pk})

    def test_lecturer_cannot_request_units_from_another_department(self):
        form = LecturerUnitRequestForm({
            'department': 'School of Computing', 'requested_units': [self.ba_slot.pk],
        })
        self.assertFalse(form.is_valid())
        self.assertIn('requested_units', form.errors)

    def test_lecturer_can_request_units_across_years(self):
        form = LecturerUnitRequestForm({
            'department': 'School of Computing',
            'requested_units': [self.cs_slot.pk, self.cs_later.pk],
        })
        self.assertTrue(form.is_valid(), form.errors)

    def test_staff_form_has_department_dropdown_not_teaching_choices(self):
        form = DepartmentEmployeeSignupForm(requested_role='STAFF')
        self.assertIn('department', form.fields)
        self.assertNotIn('requested_units', form.fields)

    def test_approval_creates_authorized_teaching_assignment(self):
        admin = User.objects.create_superuser(username='testadmin', password='SafeTestP@ss99')
        lecturer = User.objects.create_user(username='teach', password='SafeTestP@ss99', role='LECTURER')
        application = LecturerUnitRequest.objects.create(lecturer=lecturer, placement=self.cs_slot)
        application.approve(admin)
        self.assertEqual(application.status, 'APPROVED')
        self.assertTrue(UnitLecturerAssignment.objects.filter(placement=self.cs_slot, lecturer=lecturer).exists())

    def test_cannot_overwrite_another_lecturers_assignment(self):
        admin = User.objects.create_superuser(username='testadmin2', password='SafeTestP@ss99')
        owner = User.objects.create_user(username='owner', password='SafeTestP@ss99', role='LECTURER')
        contender = User.objects.create_user(username='contender', password='SafeTestP@ss99', role='LECTURER')
        UnitLecturerAssignment.objects.create(placement=self.cs_slot, lecturer=owner)
        application = LecturerUnitRequest.objects.create(lecturer=contender, placement=self.cs_slot)
        with self.assertRaises(ValidationError):
            application.approve(admin)
        self.assertEqual(UnitLecturerAssignment.objects.get(placement=self.cs_slot).lecturer_id, owner.pk)

    def test_non_lecturer_cannot_enter_teaching_dashboard(self):
        student = User.objects.create_user(username='teststudent', password='SafeTestP@ss99', role='STUDENT')
        self.client.force_login(student)
        self.assertEqual(self.client.get(reverse('campus_departments:my_teaching')).status_code, 403)
