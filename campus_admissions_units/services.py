"""Common decisions are enforced on the server, never only in JavaScript."""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from academics.models import StudentProgramme
from .models import GRADES, ProgrammeRequirement, ProgrammeApplication, SemesterRegistration, RegisteredUnit, UnitLecturerAssignment


def grade_meets(actual, minimum):
    return actual in GRADES and minimum in GRADES and GRADES.index(actual) <= GRADES.index(minimum)


def preliminary_match(programme, grade, points):
    if not programme.is_active or not grade or points is None:
        return False
    try:
        requirement = programme.admission_requirement
    except ProgrammeRequirement.DoesNotExist:
        return False
    return (requirement.applications_open and grade_meets(grade, requirement.minimum_mean_grade)
            and Decimal(str(points)) >= requirement.minimum_cluster_points)


def get_unit_lecturer(placement):
    try:
        assignment = placement.review_assignment
    except UnitLecturerAssignment.DoesNotExist:
        assignment = None
    if assignment:
        return assignment.lecturer if assignment.lecturer.is_active else None
    if placement.lms_course_id and placement.lms_course.lecturer_id:
        lecturer = placement.lms_course.lecturer
        return lecturer if lecturer.is_active else None
    return None


def place_approved_applicant(admission):
    """Approval allocates a programme; existing academic assignments never overwritten."""
    try:
        choice = admission.programme_application
    except ProgrammeApplication.DoesNotExist:
        # Legacy students do not have a new programme application.
        return None
    record, _created = StudentProgramme.objects.get_or_create(
        student=admission.user,
        defaults={"programme": choice.programme, "current_year": 1, "current_semester": 1,
                  "status": StudentProgramme.Status.ACTIVE},
    )
    return record


@transaction.atomic
def review_unit(unit_request, lecturer, approve, note=""):
    """Review only a unit genuinely assigned to the currently logged-in lecturer."""
    unit_request = (
        RegisteredUnit.objects.select_for_update()
        .select_related("registration__student_programme__student", "placement__lms_course__lecturer", "placement__unit")
        .get(pk=unit_request.pk)
    )
    if unit_request.status != RegisteredUnit.Status.PENDING:
        raise ValueError("This unit request was already reviewed.")
    if get_unit_lecturer(unit_request.placement) != lecturer:
        raise PermissionError("You are not assigned to approve this unit.")
    unit_request.status = RegisteredUnit.Status.APPROVED if approve else RegisteredUnit.Status.REJECTED
    unit_request.reviewed_by = lecturer
    unit_request.reviewed_at = timezone.now()
    unit_request.review_note = (note or "")[:300]
    unit_request.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note"])
    # Only approved requests with a linked teaching course enrol students.
    if approve and unit_request.placement.lms_course_id:
        from courses.models import Enrollment
        Enrollment.objects.get_or_create(
            student=unit_request.registration.student_programme.student,
            course_id=unit_request.placement.lms_course_id,
        )
    statuses = list(unit_request.registration.units.values_list("status", flat=True))
    if all(s == RegisteredUnit.Status.APPROVED for s in statuses):
        status = SemesterRegistration.Status.APPROVED
    elif all(s == RegisteredUnit.Status.REJECTED for s in statuses):
        status = SemesterRegistration.Status.REJECTED
    elif any(s != RegisteredUnit.Status.PENDING for s in statuses):
        status = SemesterRegistration.Status.PARTIAL
    else:
        status = SemesterRegistration.Status.SUBMITTED
    unit_request.registration.status = status
    unit_request.registration.reviewed_at = timezone.now()
    unit_request.registration.save(update_fields=["status", "reviewed_at"])
    return unit_request
