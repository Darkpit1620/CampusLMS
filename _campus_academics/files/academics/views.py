from collections import defaultdict

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_GET
from courses.models import Enrollment

from .models import Programme, ProgrammeUnit, StudentProgramme


@require_GET
def programme_list(request):
    programmes = Programme.objects.filter(is_active=True)
    query = request.GET.get("q", "").strip()[:100]
    department = request.GET.get("department", "").strip()[:140]
    if query:
        programmes = programmes.filter(
            Q(code__icontains=query) | Q(name__icontains=query) | Q(department__icontains=query)
        )
    if department:
        programmes = programmes.filter(department=department)
    programmes = programmes.order_by("department", "name")
    departments = (
        Programme.objects.filter(is_active=True)
        .exclude(department="")
        .order_by("department")
        .values_list("department", flat=True)
        .distinct()
    )
    return render(request, "academics/programme_list.html", {
        "programmes": programmes, "query": query,
        "selected_department": department, "departments": departments,
    })


@require_GET
def programme_detail(request, code):
    programme = get_object_or_404(Programme, code__iexact=code, is_active=True)
    placements = ProgrammeUnit.objects.filter(programme=programme).select_related("unit", "lms_course").order_by("year", "semester", "unit__code")
    groups = defaultdict(list)
    for placement in placements:
        groups[(placement.year, placement.semester)].append(placement)
    terms = [
        {"year": year, "semester": semester, "units": groups.get((year, semester), [])}
        for year in range(1, programme.duration_years + 1)
        for semester in (1, 2, 3)
    ]
    return render(request, "academics/programme_detail.html", {"programme": programme, "terms": terms})


@login_required(login_url="/access/student/login/")
@require_GET
def my_units(request):
    if request.user.role != "STUDENT" or request.user.is_superuser or request.user.is_staff:
        raise PermissionDenied("This page is for students only.")
    record = StudentProgramme.objects.select_related("programme").filter(student=request.user).first()
    rows = []
    if record:
        placements = ProgrammeUnit.objects.filter(
            programme=record.programme, year=record.current_year,
            semester=record.current_semester,
        ).select_related("unit", "lms_course").order_by("unit__code")
        course_ids = [p.lms_course_id for p in placements if p.lms_course_id]
        enrolled_ids = set(Enrollment.objects.filter(
            student=request.user, course_id__in=course_ids
        ).values_list("course_id", flat=True)) if course_ids else set()
        rows = [
            {"placement": p, "can_open": bool(p.lms_course_id and p.lms_course_id in enrolled_ids)}
            for p in placements
        ]
    return render(request, "academics/my_units.html", {"record": record, "rows": rows})
