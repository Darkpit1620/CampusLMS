"""Bridge approved curriculum unit teaching assignments to existing LMS courses.

Never changes a course assigned to somebody else. Existing CSC101 materials,
submissions and grades remain attached to the same course.
"""
from django.core.exceptions import ValidationError
from django.db import transaction
from courses.models import Course


def _course_code_for(placement):
    field = Course._meta.get_field('code')
    maximum = field.max_length or 32
    # Stable, distinct code for a specific curriculum placement.
    code = f'U{placement.pk:07d}'
    if len(code) > maximum:
        code = 'U' + str(placement.pk)
    if len(code) > maximum:
        raise ValidationError('LMS course code field is too short for this unit. Contact the administrator.')
    return code


def _required_field_warnings():
    names = {f.name for f in Course._meta.concrete_fields}
    missing = {'code', 'title', 'lecturer'} - names
    if missing:
        raise ValidationError('Cannot create a teaching course: Course model is missing fields: ' + ', '.join(sorted(missing)))


@transaction.atomic
def ensure_teaching_course(placement, lecturer):
    """Idempotently link an authorized lecturer's approved placement to a course."""
    from academics.models import ProgrammeUnit
    from campus_admissions_units.models import UnitLecturerAssignment

    placement = ProgrammeUnit.objects.select_for_update().select_related('unit', 'programme', 'lms_course').get(pk=placement.pk)
    approved = UnitLecturerAssignment.objects.filter(placement=placement, lecturer=lecturer).exists()
    if not approved or lecturer.role != 'LECTURER' or not lecturer.is_active:
        raise ValidationError('Only a currently approved active lecturer can receive a teaching course.')
    _required_field_warnings()
    if placement.lms_course_id:
        if placement.lms_course.lecturer_id != lecturer.pk:
            raise ValidationError(
                f'{placement.unit.code}: linked teaching course belongs to a different lecturer. '
                'An administrator must resolve the conflict; no course was reassigned.'
            )
        return placement.lms_course

    # Reuse a legacy teaching course only if its instructor already matches.
    old = Course.objects.filter(code=placement.unit.code, lecturer=lecturer).first()
    if old is not None:
        course = old
    else:
        code = _course_code_for(placement)
        existing = Course.objects.filter(code=code).first()
        if existing:
            if existing.lecturer_id != lecturer.pk:
                raise ValidationError(f'LMS course code {code} is already used by another lecturer.')
            course = existing
        else:
            limit = Course._meta.get_field('title').max_length or 200
            name = (
                f'{placement.unit.title} ({placement.programme.code} '
                f'Year {placement.year} Semester {placement.semester})'
            )[:limit]
            try:
                course = Course.objects.create(code=code, title=name, lecturer=lecturer)
            except Exception as error:
                # Django versions and installed Course definitions may have extra
                # mandatory fields. Never bypass a model constraint to make a class.
                raise ValidationError(
                    'Could not create a teaching course for ' + placement.unit.code +
                    '. Check the Course model requirements in courses/models.py. '
                    f'Original error: {type(error).__name__}: {error}'
                ) from error

    placement.lms_course = course
    placement.save(update_fields=['lms_course'])
    return course
