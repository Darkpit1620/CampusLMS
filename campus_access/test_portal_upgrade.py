from datetime import date
from django.test import TestCase, override_settings
from django.core import mail
from django.urls import reverse
from accounts.models import User
from admissions.models import StudentAdmission
from campus_access.models import EmployeeApplication
from campus_access.notifications import send_student_approval_email, send_employee_approval_email

PASSWORD = "CorrectHorse-Excellent-2026!"


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class PortalUpgradeTests(TestCase):
    def test_main_page_is_portal(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Student Portal")
        self.assertContains(response, "Lecturer Portal")

    def test_student_approval_email_and_login(self):
        user = User.objects.create_user(
            username="student_v2", email="student@example.com",
            password=PASSWORD, role="STUDENT", is_active=False,
        )
        application = StudentAdmission.objects.create(user=user, date_of_birth=date(2001, 1, 1))
        application.approve()
        send_student_approval_email(application)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(application.admission_number, mail.outbox[0].body)
        self.assertNotIn(PASSWORD, mail.outbox[0].body)
        logged_in = self.client.post(reverse("campus_access:role_login", args=["student"]), {
            "username": application.admission_number, "password": PASSWORD,
        })
        self.assertRedirects(logged_in, reverse("dashboard"))

    def test_employee_registration_number_is_stable_and_logs_in(self):
        user = User.objects.create_user(
            username="prof@example.com", email="prof@example.com",
            password=PASSWORD, role="LECTURER", is_active=False,
        )
        application = EmployeeApplication.objects.create(
            user=user, requested_role="LECTURER", phone_number="+254712345678",
            country="KE", date_of_birth=date(1990, 1, 1), department="Chemistry",
        )
        application.approve()
        number = application.registration_number
        self.assertTrue(number.startswith("CLMS-LEC-"))
        application.approve()
        self.assertEqual(application.registration_number, number)
        send_employee_approval_email(application)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(number, mail.outbox[0].body)
        good = self.client.post(reverse("campus_access:role_login", args=["lecturer"]), {
            "username": number, "password": PASSWORD,
        })
        self.assertRedirects(good, reverse("dashboard"))

    def test_incorrect_password_is_not_accepted(self):
        user = User.objects.create_user(
            username="lecturer_legacy", password=PASSWORD, role="LECTURER", is_active=True,
        )
        response = self.client.post(reverse("campus_access:role_login", args=["lecturer"]), {
            "username": user.username, "password": "incorrect-password",
        })
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
