from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Programme, ProgrammeUnit, StudentProgramme, Unit


class AcademicStructureTests(TestCase):
    def setUp(self):
        self.student = get_user_model().objects.create_user(
            username="sample_student", password="a-strong-test-password-2026", role="STUDENT"
        )
        self.lecturer = get_user_model().objects.create_user(
            username="sample_lecturer", password="a-different-test-password-2026", role="LECTURER"
        )
        self.programme = Programme.objects.create(code="TEST-CS", name="Test Computer Science")
        self.unit = Unit.objects.create(code="TEST-101", title="Test Foundations")
        ProgrammeUnit.objects.create(programme=self.programme, unit=self.unit, year=1, semester=1)

    def test_public_catalogue(self):
        response = self.client.get(reverse("academics:programme_list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Computer Science")

    def test_all_twelve_semesters_listed(self):
        response = self.client.get(reverse("academics:programme_detail", args=["TEST-CS"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Test Foundations")
        self.assertContains(response, "Year 4")
        self.assertContains(response, "Semester 3")

    def test_student_needs_login(self):
        response = self.client.get(reverse("academics:my_units"))
        self.assertEqual(response.status_code, 302)

    def test_unassigned_student_sees_guidance(self):
        self.client.force_login(self.student)
        response = self.client.get(reverse("academics:my_units"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "not been assigned yet")

    def test_assigned_student_sees_only_current_semester(self):
        later = Unit.objects.create(code="TEST-102", title="Next Semester")
        ProgrammeUnit.objects.create(programme=self.programme, unit=later, year=1, semester=2)
        StudentProgramme.objects.create(student=self.student, programme=self.programme, current_year=1, current_semester=1)
        self.client.force_login(self.student)
        response = self.client.get(reverse("academics:my_units"))
        self.assertContains(response, "Test Foundations")
        self.assertNotContains(response, "Next Semester")

    def test_lecturer_cannot_view_student_units(self):
        self.client.force_login(self.lecturer)
        self.assertEqual(self.client.get(reverse("academics:my_units")).status_code, 403)
