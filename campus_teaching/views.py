"""Teaching pages use approved unit assignments as authorization source.

No role-only bypass: lecturers may change only their own assigned units.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from academics.models import ProgrammeUnit
from campus_admissions_units.models import UnitLecturerAssignment
from campus_departments.models import LecturerUnitRequest
from assignments.models import Assignment
from courses.models import CourseMaterial
from .forms import assignment_form, material_form
from .services import ensure_teaching_course


def lecturer_only(request):
    user = request.user
    # is_staff is a Django admin flag, not a university employment role.
    if not user.is_active or user.role != 'LECTURER' or user.is_superuser:
        raise PermissionDenied('Approved lecturer account required.')


def authorized_placement(request, placement_id):
    lecturer_only(request)
    assignment = get_object_or_404(
        UnitLecturerAssignment.objects.select_related(
            'placement__unit', 'placement__programme', 'placement__lms_course',
        ),
        placement_id=placement_id, lecturer=request.user,
    )
    # Course-level permissions are still enforced. Teaching other lecturers'
    # courses or creating assignments in unlinked courses is never allowed.
    return assignment.placement


def linked_course(request, placement_id):
    placement = authorized_placement(request, placement_id)
    course = placement.lms_course
    if course is None:
        raise ValidationError('This approved teaching unit has no linked LMS course. Ask the admin to run the course sync.')
    if course.lecturer_id != request.user.pk:
        raise PermissionDenied('This teaching course is assigned to another lecturer.')
    return placement, course


@login_required
@require_GET
def teaching_dashboard(request):
    lecturer_only(request)
    assignments = list(
        UnitLecturerAssignment.objects.filter(lecturer=request.user)
        .select_related('placement__unit', 'placement__programme', 'placement__lms_course')
        .order_by('placement__programme__name', 'placement__year', 'placement__semester', 'placement__unit__code')
    )
    pending = list(LecturerUnitRequest.objects.filter(
        lecturer=request.user, status=LecturerUnitRequest.Status.PENDING,
    ).select_related('placement__unit', 'placement__programme').order_by('placement__unit__code'))
    counts = {
        a.placement.lms_course_id: 0 for a in assignments if a.placement.lms_course_id
    }
    if counts:
        totals = (Assignment.objects.filter(course_id__in=list(counts))
                  .values('course_id').annotate(total=Count('id')))
        counts.update({row['course_id']: row['total'] for row in totals})
    rows = [{
        'placement': a.placement,
        'ready': bool(a.placement.lms_course_id and a.placement.lms_course.lecturer_id == request.user.pk),
        'assignment_count': counts.get(a.placement.lms_course_id, 0),
    } for a in assignments]
    return render(request, 'campus_teaching/dashboard.html', {
        'rows': rows, 'pending': pending,
        'approved_count': len(rows), 'pending_count': len(pending),
    })


@login_required
@require_GET
def unit_workspace(request, placement_id):
    placement = authorized_placement(request, placement_id)
    course = placement.lms_course
    ready = bool(course and course.lecturer_id == request.user.pk)
    materials = CourseMaterial.objects.filter(course=course).order_by('-pk')[:30] if ready else []
    assignments = Assignment.objects.filter(course=course).order_by('-pk')[:30] if ready else []
    return render(request, 'campus_teaching/unit.html', {
        'placement': placement, 'course': course, 'ready': ready,
        'materials': materials, 'assignments': assignments,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def upload_resource(request, placement_id):
    try:
        placement, course = linked_course(request, placement_id)
    except ValidationError as error:
        messages.error(request, '; '.join(error.messages))
        return redirect('campus_teaching:unit', placement_id=placement_id)
    try:
        form_class = material_form()
    except ValueError as error:
        messages.error(request, str(error))
        return redirect('campus_teaching:unit', placement_id=placement_id)
    form = form_class(request.POST or None, request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        record.course = course
        names = {f.name for f in CourseMaterial._meta.fields}
        for name in ('uploaded_by', 'lecturer', 'created_by'):
            if name in names:
                setattr(record, name, request.user)
        record.save()
        messages.success(request, 'Learning material uploaded to this unit.')
        return redirect('campus_teaching:unit', placement_id=placement_id)
    return render(request, 'campus_teaching/resource_form.html', {
        'placement': placement, 'form': form,
    })


@login_required
@require_http_methods(['GET', 'POST'])
def create_assignment(request, placement_id):
    try:
        placement, course = linked_course(request, placement_id)
    except ValidationError as error:
        messages.error(request, '; '.join(error.messages))
        return redirect('campus_teaching:unit', placement_id=placement_id)
    try:
        form_class = assignment_form()
    except ValueError as error:
        messages.error(request, str(error))
        return redirect('campus_teaching:unit', placement_id=placement_id)
    form = form_class(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        record = form.save(commit=False)
        record.course = course
        names = {f.name for f in Assignment._meta.fields}
        for name in ('created_by', 'lecturer', 'uploaded_by'):
            if name in names:
                setattr(record, name, request.user)
        record.save()
        messages.success(request, 'Assignment created for this unit.')
        return redirect('campus_teaching:unit', placement_id=placement_id)
    return render(request, 'campus_teaching/assignment_form.html', {
        'placement': placement, 'form': form,
    })
