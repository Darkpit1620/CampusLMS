"""Lecturer requests are separate from approved teaching assignments.

Self-service choice MUST NOT grant permission to teach or review students.
The existing UnitLecturerAssignment remains the source of truth.
"""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils import timezone


class LecturerDepartmentPreference(models.Model):
    lecturer = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='department_preference', limit_choices_to={'role': 'LECTURER'},
    )
    department = models.CharField(max_length=140)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.lecturer.get_username()} — {self.department}'


class LecturerUnitRequest(models.Model):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Awaiting approval'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'

    lecturer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name='teaching_requests', limit_choices_to={'role': 'LECTURER'},
    )
    placement = models.ForeignKey(
        'academics.ProgrammeUnit', on_delete=models.PROTECT,
        related_name='lecturer_requests',
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='teaching_requests_reviewed',
    )
    review_note = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [models.UniqueConstraint(
            fields=('lecturer', 'placement'), name='department_unique_lecturer_unit_request'
        )]

    def __str__(self):
        return f'{self.lecturer.get_username()} requests {self.placement}'

    @transaction.atomic
    def approve(self, administrator):
        """Explicit administrator review; never overwrite another lecturer's unit."""
        from campus_admissions_units.models import UnitLecturerAssignment

        if not administrator.is_active or not administrator.is_superuser:
            raise ValidationError('Only an active university superuser may approve unit requests.')
        record = LecturerUnitRequest.objects.select_for_update().select_related(
            'lecturer', 'placement__lms_course__lecturer',
        ).get(pk=self.pk)
        if record.status == self.Status.REJECTED:
            raise ValidationError('Rejected requests require a fresh review request.')
        if record.lecturer.role != 'LECTURER' or not record.lecturer.is_active:
            raise ValidationError('Approve and activate the lecturer account first.')
        if not record.placement.programme.is_active:
            raise ValidationError('This programme is inactive.')
        placement = record.placement
        if placement.lms_course_id and placement.lms_course.lecturer_id not in (None, record.lecturer_id):
            raise ValidationError('Linked LMS course belongs to another lecturer. Reassign it explicitly first.')
        existing = UnitLecturerAssignment.objects.filter(placement=placement).first()
        if existing and existing.lecturer_id != record.lecturer_id:
            raise ValidationError('This unit is already allocated to another lecturer. Reassign it explicitly first.')
        if existing is None:
            UnitLecturerAssignment.objects.create(placement=placement, lecturer=record.lecturer)
        record.status = self.Status.APPROVED
        record.reviewed_by = administrator
        record.review_note = ''
        record.reviewed_at = timezone.now()
        record.save(update_fields=('status', 'reviewed_by', 'review_note', 'reviewed_at'))
        self.status = record.status

    def reject(self, administrator, note=''):
        if not administrator.is_active or not administrator.is_superuser:
            raise ValidationError('Only an active university superuser may reject unit requests.')
        if self.status == self.Status.APPROVED:
            raise ValidationError('An approved teaching allocation must be changed separately.')
        self.status = self.Status.REJECTED
        self.reviewed_by = administrator
        self.review_note = (note or '')[:300]
        self.reviewed_at = timezone.now()
        self.save(update_fields=('status', 'reviewed_by', 'review_note', 'reviewed_at'))
