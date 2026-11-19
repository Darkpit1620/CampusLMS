"""Safety checks for the Stage 16 department/unit dropdown behaviour."""
from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from academics.models import Programme, ProgrammeUnit, Unit, StudentProgramme
from accounts.models import User
from campus_admissions_units.models import ProgrammeRequirement, SemesterRegistration, RegisteredUnit
from campus_departments.forms import DepartmentEmployeeSignupForm, LecturerUnitRequestForm


class SemesterDropdownTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.eng = Programme.objects.create(code='S16-ENG', name='Test Engineering', department='School of Engineering')
        cls.agri = Programme.objects.create(code='S16-AGR', name='Test Agriculture', department='School of Agriculture')
        a = Unit.objects.create(code='S16-E101', title='Engineering Foundations')
        b = Unit.objects.create(code='S16-A101', title='Agricultural Foundations')
        c = Unit.objects.create(code='S16-E201', title='Engineering Year Two')
        cls.eng_first = ProgrammeUnit.objects.create(programme=cls.eng, unit=a, year=1, semester=1)
        cls.agri_first = ProgrammeUnit.objects.create(programme=cls.agri, unit=b, year=1, semester=1)
        cls.eng_second = ProgrammeUnit.objects.create(programme=cls.eng, unit=c, year=2, semester=2)
        ProgrammeRequirement.objects.create(programme=cls.eng, minimum_cluster_points=Decimal('20'))
        ProgrammeRequirement.objects.create(programme=cls.agri, minimum_cluster_points=Decimal('20'))

    def test_department_dropdown_endpoint_filters_and_gives_programme_ids(self):
        result = self.client.get(reverse('campus_departments:unit_options'), {'department': 'School of Engineering'})
        self.assertEqual(result.status_code, 200)
        units = result.json()['units']
        self.assertEqual({u['id'] for u in units}, {self.eng_first.pk, self.eng_second.pk})
        self.assertTrue(all(u['programme_id'] == self.eng.pk for u in units))
        self.assertEqual({u['year'] for u in units}, {1, 2})

    def test_unrelated_department_unit_rejected_server_side(self):
        form = LecturerUnitRequestForm({'department': 'School of Engineering', 'requested_units':[self.agri_first.pk]})
        self.assertFalse(form.is_valid())
        self.assertIn('requested_units', form.errors)

    def test_lecturer_can_choose_some_units_not_every_unit(self):
        form = LecturerUnitRequestForm({'department': 'School of Engineering', 'requested_units':[self.eng_second.pk]})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual([u.pk for u in form.cleaned_data['requested_units']], [self.eng_second.pk])

    def test_student_gets_only_current_programme_and_term_units(self):
        person = User.objects.create_user(username='stage16student', password='TemporaryPass123!')
        programme = StudentProgramme.objects.create(student=person, programme=self.eng, current_year=1, current_semester=1)
        self.client.force_login(person)
        result = self.client.get(reverse('campus_admissions_units:register_units'))
        self.assertEqual(result.status_code, 200)
        self.assertContains(result, 'Engineering Foundations')
        self.assertNotContains(result, 'Engineering Year Two')
        self.assertNotContains(result, 'Agricultural Foundations')
        submitted = self.client.post(reverse('campus_admissions_units:register_units'), {'units':[str(self.eng_first.pk)]})
        self.assertEqual(submitted.status_code, 302)
        registration = SemesterRegistration.objects.get(student_programme=programme)
        self.assertEqual(RegisteredUnit.objects.get(registration=registration).placement, self.eng_first)
