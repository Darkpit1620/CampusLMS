from decimal import Decimal
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from academics.models import Programme, ProgrammeUnit, StudentProgramme, Unit
from admissions.models import StudentAdmission
from .models import (ProgrammeRequirement, ProgrammeApplication, RegisteredUnit,
                     SemesterRegistration, UnitLecturerAssignment, ProgrammeLecturerAllocation)
from .services import grade_meets, preliminary_match


class AdmissionAndUnitWorkflowTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.student = User.objects.create_user(username="test-student", password="Valid-Pass123!", role="STUDENT")
        cls.lecturer = User.objects.create_user(username="test-lecturer", password="Valid-Pass123!", role="LECTURER")
        cls.other_lecturer = User.objects.create_user(username="test-lecturer2", password="Valid-Pass123!", role="LECTURER")
        cls.programme = Programme.objects.create(code="TEST-BSC", name="Test Degree Programme", duration_years=4)
        cls.rule = ProgrammeRequirement.objects.create(
            programme=cls.programme, minimum_mean_grade="C+", minimum_cluster_points=Decimal("30.0"),
            requirements_verified=False,
        )
        cls.unit1 = Unit.objects.create(code="TST101", title="First Test Unit")
        cls.unit2 = Unit.objects.create(code="TST102", title="Second Test Unit")
        cls.placement1 = ProgrammeUnit.objects.create(programme=cls.programme, unit=cls.unit1, year=1, semester=1)
        cls.placement2 = ProgrammeUnit.objects.create(programme=cls.programme, unit=cls.unit2, year=1, semester=1)
        cls.sp = StudentProgramme.objects.create(student=cls.student, programme=cls.programme, current_year=1, current_semester=1)

    def test_eligibility_finder_filters_below_cutoff(self):
        self.assertTrue(grade_meets("B", "C+"))
        self.assertFalse(grade_meets("C", "C+"))
        self.assertTrue(preliminary_match(self.programme, "B", Decimal("32")))
        self.assertFalse(preliminary_match(self.programme, "B", Decimal("29")))
        data = self.client.get(reverse("campus_admissions_units:programme_finder"), {"grade": "B", "points": "31"}).json()
        self.assertIn(self.programme.code, [row["code"] for row in data["programmes"]])
        data = self.client.get(reverse("campus_admissions_units:programme_finder"), {"grade": "C", "points": "31"}).json()
        self.assertNotIn(self.programme.code, [row["code"] for row in data["programmes"]])

    def test_approved_existing_admission_creates_placement_without_replacing_user(self):
        second = User.objects.create_user(username="new_applicant", role="STUDENT", password="Valid-Pass123!", is_active=False)
        admission = StudentAdmission.objects.create(user=second)
        ProgrammeApplication.objects.create(
            admission=admission, programme=self.programme,
            kcse_mean_grade="B", reported_cluster_points=Decimal("35"),
        )
        admission.approve()
        second.refresh_from_db()
        placement = StudentProgramme.objects.get(student=second)
        self.assertTrue(second.is_active)
        self.assertEqual(placement.programme_id, self.programme.pk)
        self.assertTrue(admission.admission_number)
        admission.approve()
        self.assertEqual(StudentProgramme.objects.filter(student=second).count(), 1)

    def test_semester_registration_avoids_duplicate_submissions(self):
        self.client.force_login(self.student)
        url = reverse("campus_admissions_units:register_units")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response = self.client.post(url, {"units": [str(self.placement1.pk), str(self.placement2.pk)]})
        self.assertEqual(response.status_code, 302)
        registration = SemesterRegistration.objects.get(student_programme=self.sp)
        self.assertEqual(registration.units.count(), 2)
        self.client.post(url, {"units": [str(self.placement1.pk), str(self.placement2.pk)]})
        self.assertEqual(SemesterRegistration.objects.filter(student_programme=self.sp).count(), 1)

    def test_cannot_register_unit_outside_students_semester(self):
        another_unit = Unit.objects.create(code="TST201", title="Later Unit")
        wrong_placement = ProgrammeUnit.objects.create(programme=self.programme, unit=another_unit, year=2, semester=2)
        self.client.force_login(self.student)
        resp = self.client.post(reverse("campus_admissions_units:register_units"), {"units": [str(wrong_placement.pk)]})
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(SemesterRegistration.objects.filter(student_programme=self.sp).exists())

    def test_only_assigned_lecturer_can_approve(self):
        reg = SemesterRegistration.objects.create(student_programme=self.sp, year=1, semester=1)
        item = RegisteredUnit.objects.create(registration=reg, placement=self.placement1)
        UnitLecturerAssignment.objects.create(placement=self.placement1, lecturer=self.lecturer)
        url = reverse("campus_admissions_units:lecturer_review", args=[item.pk])
        self.client.force_login(self.other_lecturer)
        self.assertEqual(self.client.post(url, {"decision": "approve"}).status_code, 403)
        item.refresh_from_db()
        self.assertEqual(item.status, RegisteredUnit.Status.PENDING)
        self.client.force_login(self.lecturer)
        self.assertEqual(self.client.post(url, {"decision": "approve"}).status_code, 302)
        item.refresh_from_db()
        self.assertEqual(item.status, RegisteredUnit.Status.APPROVED)
        self.assertEqual(item.reviewed_by_id, self.lecturer.pk)
        self.assertEqual(self.client.post(url, {"decision": "approve"}).status_code, 302)
        self.assertEqual(RegisteredUnit.objects.filter(registration=reg).count(), 1)

    def test_bulk_lecturer_allocation_for_term(self):
        allocation = ProgrammeLecturerAllocation.objects.create(
            programme=self.programme, lecturer=self.lecturer, year=1, semester=1,
        )
        self.assertEqual(allocation.apply_to_units(), 2)
        self.assertEqual(UnitLecturerAssignment.objects.filter(lecturer=self.lecturer).count(), 2)
