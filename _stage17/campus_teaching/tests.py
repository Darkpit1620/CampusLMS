"""Unit-level authorization tests; use existing schema and migrations."""
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.urls import reverse
from academics.models import Programme, Unit, ProgrammeUnit
from campus_admissions_units.models import UnitLecturerAssignment
from .services import ensure_teaching_course


class TeachingUnitTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.lecturer = User.objects.create_user(username='unit_lec_a', password='safe-test-password', role='LECTURER')
        self.other = User.objects.create_user(username='unit_lec_b', password='safe-test-password', role='LECTURER')
        self.student = User.objects.create_user(username='unit_student_a', password='safe-test-password', role='STUDENT')
        self.programme = Programme.objects.create(code='ST17-TEST', name='Test Programme', department='School of Engineering')
        self.unit = Unit.objects.create(code='ST17-UNIT', title='Engineering Test Unit')
        self.placement = ProgrammeUnit.objects.create(programme=self.programme, unit=self.unit, year=1, semester=1)
        self.assignment = UnitLecturerAssignment.objects.create(placement=self.placement, lecturer=self.lecturer)

    def test_approved_unit_is_linked_to_teacher(self):
        self.placement.refresh_from_db()
        self.assertIsNotNone(self.placement.lms_course_id)
        self.assertEqual(self.placement.lms_course.lecturer_id, self.lecturer.pk)
        course = ensure_teaching_course(self.placement, self.lecturer)
        self.assertEqual(self.placement.lms_course_id, course.pk)

    def test_lecturer_can_open_own_dashboard_and_unit(self):
        self.client.force_login(self.lecturer)
        self.assertEqual(self.client.get(reverse('campus_teaching:dashboard')).status_code, 200)
        self.assertEqual(self.client.get(reverse('campus_teaching:unit', args=[self.placement.pk])).status_code, 200)

    def test_other_lecturer_cannot_upload_or_create_assignment(self):
        self.client.force_login(self.other)
        for endpoint in ('unit', 'upload', 'assignment_create'):
            result = self.client.get(reverse('campus_teaching:' + endpoint, args=[self.placement.pk]))
            self.assertEqual(result.status_code, 404)

    def test_student_cannot_open_lecturer_dashboard(self):
        self.client.force_login(self.student)
        self.assertEqual(self.client.get(reverse('campus_teaching:dashboard')).status_code, 403)
