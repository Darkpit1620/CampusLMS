from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from .models import StudentAdmission


class StudentAdmissionTests(TestCase):
    def test_registration_is_pending_and_inactive(self):
        response = self.client.post(reverse("admissions:register"), {
            "first_name": "Example", "last_name": "Student",
            "email": "student-test@example.com",
            "phone_number": "+254712345678",
            "date_of_birth": "2001-05-14",
            "password1": "VeryStrongTestPassword#849",
            "password2": "VeryStrongTestPassword#849",
        })
        self.assertRedirects(response, reverse("admissions:pending"))
        user = User.objects.get(email="student-test@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(user.student_admission.status, "PENDING")
        self.assertIsNone(user.student_admission.admission_number)

    def test_admission_number_login_and_student_username_block(self):
        user = User.objects.create_user(
            username="existingstudent",
            password="VeryStrongTestPassword#849",
            role="STUDENT",
            is_active=False,
        )
        admission = StudentAdmission.objects.create(
            user=user, date_of_birth=date(2001, 5, 14),
        )
        admission.approve()
        self.assertEqual(admission.status, "APPROVED")
        self.assertTrue(User.objects.get(pk=user.pk).is_active)
        self.assertTrue(admission.admission_number.startswith("CLMS-"))
        blocked = self.client.post(reverse("login"), {
            "username": "existingstudent", "password": "VeryStrongTestPassword#849",
        })
        self.assertEqual(blocked.status_code, 200)
        self.assertFalse("_auth_user_id" in self.client.session)
        ok = self.client.post(reverse("login"), {
            "username": admission.admission_number,
            "password": "VeryStrongTestPassword#849",
        })
        self.assertRedirects(ok, reverse("dashboard"))

    def test_lecturer_username_still_works(self):
        User.objects.create_user(
            username="lecturer_test", password="VeryStrongTestPassword#849",
            role="LECTURER", is_active=True,
        )
        response = self.client.post(reverse("login"), {
            "username": "lecturer_test", "password": "VeryStrongTestPassword#849",
        })
        self.assertRedirects(response, reverse("dashboard"))
