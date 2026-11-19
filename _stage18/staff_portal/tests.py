from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from campus_access.models import EmployeeApplication
from .forms import StaffSignupForm
from .management.commands.seed_staff_departments import SEED
from .models import StaffCategory, StaffDepartment, StaffProfile

User = get_user_model()


class StaffPortalTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        for cat, name, description in SEED:
            StaffDepartment.objects.create(category=cat, name=name, description=description)

    def valid_registration(self, department="Human Resources", category="NON_TEACHING"):
        return {
            "first_name": "Grace", "last_name": "Otieno",
            "email": "grace.staff@example.com", "staff_category": category,
            "department": department, "job_title": "HR Officer",
            "phone_country": "KE", "phone_number": "0712345678",
            "date_of_birth": "1995-03-14", "password1": "SecureStaffPass2026!",
            "password2": "SecureStaffPass2026!",
        }

    def test_department_category_validation(self):
        form = StaffSignupForm(self.valid_registration(department="Games & Sports", category="TEACHING_SUPPORT"))
        self.assertFalse(form.is_valid())
        self.assertIn("department", form.errors)

    def test_staff_signup_is_inactive_and_has_no_manager_access(self):
        url = reverse("campus_access:staff_signup")
        response = self.client.post(url, self.valid_registration())
        self.assertEqual(response.status_code, 302)
        staff = User.objects.get(email="grace.staff@example.com")
        self.assertEqual(staff.role, "STAFF")
        self.assertFalse(staff.is_active)
        self.assertFalse(staff.is_staff)
        self.assertFalse(staff.is_superuser)
        application = EmployeeApplication.objects.get(user=staff)
        self.assertEqual(application.status, "PENDING")
        profile = StaffProfile.objects.get(application=application)
        self.assertEqual(profile.department.name, "Human Resources")
        self.assertFalse(profile.is_department_head)

    def test_staff_signup_form_separate_from_lecturer(self):
        response = self.client.get(reverse("campus_access:staff_signup"))
        self.assertContains(response, "Staff registration")
        self.assertContains(response, "Human Resources")
        self.assertContains(response, "staff_category")

    def test_approved_staff_sees_staff_desk(self):
        user = User.objects.create_user(
            username="staff-approved", password="TestStaffPass!42", role="STAFF", is_active=True
        )
        app = EmployeeApplication.objects.create(
            user=user, requested_role="STAFF", country="KE", phone_number="+254712345678",
            date_of_birth=date(1990, 1, 1), department="Human Resources",
            status="APPROVED", registration_number="CLMS-STF-2026-000042",
        )
        StaffProfile.objects.create(
            application=app, department=StaffDepartment.objects.get(name="Human Resources"),
            category=StaffCategory.NON_TEACHING,
        )
        self.client.force_login(user)
        response = self.client.get(reverse("campus_access:staff_workspace"))
        self.assertContains(response, "My Staff Desk")
        self.assertContains(response, "Human Resources")
        self.assertContains(response, "CLMS-STF-2026-000042")

    def test_lecturer_cannot_access_staff_desk(self):
        user = User.objects.create_user(
            username="lecturer-ex", password="TestLecturerPass!42", role="LECTURER", is_active=True
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get(reverse("campus_access:staff_workspace")).status_code, 403)

    def test_existing_staff_without_profile_can_open_desk(self):
        user = User.objects.create_user(
            username="legacy-staff", password="LegacyStaffPass!42", role="STAFF", is_active=True
        )
        self.client.force_login(user)
        self.assertContains(self.client.get(reverse("campus_access:staff_workspace")), "My Staff Desk")
