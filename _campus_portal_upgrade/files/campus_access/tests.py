from datetime import date
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from admissions.models import StudentAdmission
from .models import EmployeeApplication, StudentCountry

PASSWORD = "A-Str0ng-Passw0rd!536"


class AccessTests(TestCase):
    def test_access_page(self):
        self.assertEqual(self.client.get(reverse("campus_access:home")).status_code, 200)

    def test_student_signup_pending_and_country(self):
        response = self.client.post(reverse("campus_access:student_signup"), {
            "first_name": "Student", "last_name": "Example",
            "email": "new-student@example.com", "phone_country": "KE",
            "phone_number": "712345678", "date_of_birth": "2001-01-01",
            "password1": PASSWORD, "password2": PASSWORD,
        })
        self.assertRedirects(response, reverse("campus_access:pending"))
        obj = StudentAdmission.objects.get(user__email="new-student@example.com")
        self.assertFalse(obj.user.is_active)
        self.assertEqual(obj.phone_number, "+254712345678")
        self.assertEqual(obj.country_detail.country, "KE")

    def test_lecturer_register_and_approval(self):
        response = self.client.post(reverse("campus_access:lecturer_signup"), {
            "first_name": "New", "last_name": "Lecturer",
            "email": "prof@example.com", "phone_country": "KE",
            "phone_number": "712345678", "date_of_birth": "1992-05-01",
            "department": "Computer Science", "job_title": "Lecturer",
            "password1": PASSWORD, "password2": PASSWORD,
        })
        self.assertRedirects(response, reverse("campus_access:pending"))
        obj = EmployeeApplication.objects.get(user__email="prof@example.com")
        self.assertEqual(obj.user.role, "LECTURER")
        self.assertFalse(obj.user.is_active)
        obj.approve()
        obj.user.refresh_from_db()
        self.assertTrue(obj.user.is_active)
        response = self.client.post(reverse("campus_access:role_login", args=["lecturer"]), {
            "username": obj.user.username, "password": PASSWORD,
        })
        self.assertRedirects(response, reverse("dashboard"))

    def test_student_username_is_blocked(self):
        student = User.objects.create_user(username="student_old", role="STUDENT", password=PASSWORD, is_active=True)
        obj = StudentAdmission.objects.create(user=student, date_of_birth=date(2001, 1, 1))
        obj.approve()
        response = self.client.post(reverse("campus_access:role_login", args=["student"]), {
            "username": student.username, "password": PASSWORD,
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        response = self.client.post(reverse("campus_access:role_login", args=["student"]), {
            "username": obj.admission_number, "password": PASSWORD,
        })
        self.assertRedirects(response, reverse("dashboard"))

    def test_staff_workspace_needs_role(self):
        student = User.objects.create_user(username="test_student", role="STUDENT", password=PASSWORD)
        self.client.force_login(student)
        self.assertEqual(self.client.get(reverse("campus_access:staff_workspace")).status_code, 403)
