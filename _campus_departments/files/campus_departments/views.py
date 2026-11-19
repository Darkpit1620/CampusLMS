from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods
from academics.models import Programme
from campus_admissions_units.services import preliminary_match
from campus_admissions_units.models import GRADE_CHOICES, UnitLecturerAssignment
from .forms import LecturerUnitRequestForm, department_choices, department_units
from .models import LecturerDepartmentPreference, LecturerUnitRequest


@require_GET
def eligible_programmes(request):
    department = request.GET.get('department', '').strip()
    grade = request.GET.get('grade', '').strip().upper()
    raw_points = request.GET.get('points', '').strip()
    known = {key for key, _ in department_choices() if key}
    valid_grades = {key for key, _ in GRADE_CHOICES}
    if department not in known or grade not in valid_grades:
        return JsonResponse({'programmes': []})
    try:
        points = Decimal(raw_points)
        if not points.is_finite() or not (Decimal('0') <= points <= Decimal('48')):
            raise ValueError()
    except (ValueError, InvalidOperation):
        return JsonResponse({'programmes': []})
    programmes = Programme.objects.filter(
        is_active=True, department=department,
    ).select_related('admission_requirement').order_by('name')
    matches = []
    for programme in programmes:
        if preliminary_match(programme, grade, points):
            req = programme.admission_requirement
            matches.append({
                'id': programme.pk, 'code': programme.code,
                'name': programme.name, 'department': programme.department,
                'minimum_points': str(req.minimum_cluster_points),
                'verified': req.requirements_verified,
            })
    return JsonResponse({'programmes': matches, 'notice': 'Indicative only; official results and subject requirements need verification.'})


@require_GET
def unit_options(request):
    department = request.GET.get('department', '').strip()
    known = {key for key, _ in department_choices() if key}
    if department not in known:
        return JsonResponse({'units': []})
    units = [{
        'id': placement.pk,
        'title': f'{placement.unit.code} — {placement.unit.title}',
        'programme': f'{placement.programme.code} — {placement.programme.name}',
        'year': placement.year, 'semester': placement.semester,
    } for placement in department_units(department)]
    return JsonResponse({'units': units})


@login_required
@require_http_methods(['GET', 'POST'])
def my_teaching(request):
    user = request.user
    if user.role != 'LECTURER' or not user.is_active or user.is_staff or user.is_superuser:
        raise PermissionDenied('Lecturers only')
    preference = LecturerDepartmentPreference.objects.filter(lecturer=user).first()
    if preference:
        department = preference.department
    else:
        application = getattr(user, 'employee_application', None)
        department = application.department if application else ''
    form = LecturerUnitRequestForm(
        request.POST or None, initial={'department': department},
    )
    if request.method == 'POST' and form.is_valid():
        count = form.save(user)
        messages.success(request, f'{count} new or resubmitted teaching unit request(s) sent for approval.')
        return redirect('campus_departments:my_teaching')
    requests = LecturerUnitRequest.objects.filter(lecturer=user).select_related(
        'placement__programme', 'placement__unit',
    ).order_by('status', 'placement__year', 'placement__semester')
    assigned = UnitLecturerAssignment.objects.filter(lecturer=user).select_related(
        'placement__programme', 'placement__unit',
    ).order_by('placement__year', 'placement__semester')
    return render(request, 'campus_departments/my_teaching.html', {
        'form': form, 'requests': requests, 'assigned': assigned,
    })
