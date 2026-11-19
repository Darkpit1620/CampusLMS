from decimal import Decimal
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from academics.models import Programme, ProgrammeUnit, Unit, StudentProgramme
from .models import (FeeCharge, FeePayment, Hostel, HostelRoom, HostelAllocation,
                     StudentClearance, FinalUnitResult, GraduationPolicy,
                     GraduationApplication)
from .services import financial_statement, classification, graduation_readiness


class StudentServicesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.student = User.objects.create_user(username="svc_student", password="AnExampleSecurePass123!", role="STUDENT")
        cls.other = User.objects.create_user(username="svc_other", password="AnExampleSecurePass123!", role="STUDENT")
        cls.lecturer = User.objects.create_user(username="svc_lecturer", password="AnExampleSecurePass123!", role="LECTURER")
        cls.admin_user = User.objects.create_superuser(username="svc_admin", password="AnExampleSecurePass123!", role="ADMIN")
        cls.programme = Programme.objects.create(code="SVC-BSC", name="Student Services Test", duration_years=1)
        cls.unit = Unit.objects.create(code="SVC100", title="Services Test Unit", credits=3)
        cls.placement = ProgrammeUnit.objects.create(programme=cls.programme, unit=cls.unit, year=1, semester=1, required=True)
        cls.student_programme = StudentProgramme.objects.create(student=cls.student, programme=cls.programme, current_year=1, current_semester=1)
        cls.policy = GraduationPolicy.objects.create(programme=cls.programme, scheme="HONOURS")

    def test_student_may_only_see_own_fees(self):
        FeeCharge.objects.create(student=self.other, category="TUITION", description="Other student invoice", amount=5000, academic_year=2026, semester=1)
        FeeCharge.objects.create(student=self.student, category="TUITION", description="My own invoice", amount=1000, academic_year=2026, semester=1)
        self.client.force_login(self.student)
        response = self.client.get(reverse("campus_services:fees"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "My own invoice")
        self.assertNotContains(response, "Other student invoice")
        self.client.force_login(self.lecturer)
        self.assertEqual(self.client.get(reverse("campus_services:fees")).status_code, 403)

    def test_finance_balance_comes_from_recorded_payments(self):
        charge = FeeCharge.objects.create(student=self.student, category="TUITION", description="Tuition", amount=Decimal("10000.00"), academic_year=2026, semester=1)
        FeePayment.objects.create(charge=charge, amount=Decimal("3500"), reference="SVC-TEST-PAY-1")
        s = financial_statement(self.student)
        self.assertEqual(s["paid"], Decimal("3500"))
        self.assertEqual(s["balance"], Decimal("6500"))
        over = FeePayment(charge=charge, amount=Decimal("7000"), reference="SVC-TEST-OVER")
        with self.assertRaises(ValidationError):
            over.full_clean()

    def test_hostel_allocation_creates_invoice_once(self):
        hostel = Hostel.objects.create(name="Services Hall")
        room = HostelRoom.objects.create(hostel=hostel, number="A1", capacity=1, semester_fee=Decimal("4500"))
        allocation = HostelAllocation(student=self.student, room=room, academic_year=2026, semester=1)
        allocation.full_clean()
        allocation.save()
        self.assertEqual(FeeCharge.objects.filter(hostel_allocation=allocation).count(), 1)
        allocation.save()
        self.assertEqual(FeeCharge.objects.filter(hostel_allocation=allocation).count(), 1)
        second = HostelAllocation(student=self.other, room=room, academic_year=2026, semester=1)
        with self.assertRaises(ValidationError):
            second.full_clean()

    def test_graduation_requires_verified_final_results_not_assignment_marks(self):
        self.student_programme.status = StudentProgramme.Status.COMPLETED
        self.student_programme.save()
        charge = FeeCharge.objects.create(student=self.student, category="TUITION", description="Total Fees", amount=Decimal("1200"), academic_year=2026, semester=1)
        FeePayment.objects.create(charge=charge, amount=Decimal("1200"), reference="SVC-TEST-PAID")
        StudentClearance.objects.create(student=self.student, finance=True, library=True, hostel=True, department=True)
        self.assertFalse(graduation_readiness(self.student)["eligible"])
        result = FinalUnitResult.objects.create(student=self.student, placement=self.placement, mark=Decimal("74"), verified=False)
        self.assertFalse(graduation_readiness(self.student)["eligible"])
        result.verified = True
        result.save()
        info = classification(self.student)
        self.assertTrue(info["complete"])
        self.assertEqual(info["average"], Decimal("74.00"))
        self.assertIn("First Class", info["label"])
        self.assertTrue(graduation_readiness(self.student)["eligible"])
        self.client.force_login(self.student)
        res = self.client.post(reverse("campus_services:graduation"))
        self.assertEqual(res.status_code, 302)
        app = GraduationApplication.objects.get(student=self.student)
        with self.assertRaises(ValidationError):
            app.approve(self.lecturer)
        app.approve(self.admin_user)
        self.assertEqual(app.status, GraduationApplication.Status.APPROVED)

    def test_no_fee_statement_is_not_clearance(self):
        self.student_programme.status = StudentProgramme.Status.COMPLETED
        self.student_programme.save()
        FinalUnitResult.objects.create(student=self.student, placement=self.placement, mark=Decimal("78"), verified=True)
        StudentClearance.objects.create(student=self.student, finance=True, library=True, hostel=True, department=True)
        ready = graduation_readiness(self.student)
        self.assertFalse(ready["eligible"])
        self.assertIn("Finance office has not issued a fee statement", ready["blockers"])

    def test_student_cannot_submit_graduation_before_clearance(self):
        self.client.force_login(self.student)
        response = self.client.post(reverse("campus_services:graduation"))
        self.assertEqual(response.status_code, 302)
        self.assertFalse(GraduationApplication.objects.filter(student=self.student).exists())
