from decimal import Decimal, InvalidOperation
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseBadRequest, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from academics.models import Programme, ProgrammeUnit, StudentProgramme
from .forms import ApplicantSignupForm
from campus_departments.forms import DepartmentStudentSignupForm
from .models import ProgrammeRequirement, RegisteredUnit, SemesterRegistration, UnitLecturerAssignment
from .services import get_unit_lecturer, preliminary_match, review_unit


def require_role(request, role):
    if (request.user.role != role or not request.user.is_active or request.user.is_superuser):
        raise PermissionDenied(f"{role.title()} portal only")


@require_GET
def programme_finder(request):
    grade = request.GET.get("grade", "").strip().upper()
    raw = request.GET.get("points", "").strip()
    try:
        points = Decimal(raw)
        if not points.is_finite() or not (Decimal("0") <= points <= Decimal("48")):
            raise ValueError
    except (InvalidOperation, ValueError):
        points = None
    programmes = (Programme.objects.filter(is_active=True)
                  .select_related("admission_requirement").order_by("department", "name"))
    matches = []
    if grade and points is not None:
        for p in programmes:
            if preliminary_match(p, grade, points):
                req = p.admission_requirement
                matches.append({
                    "id": p.pk,
                    "code": p.code,
                    "name": p.name,
                    "department": p.department,
                    "minimum_points": str(req.minimum_cluster_points),
                    "minimum_grade": req.minimum_mean_grade,
                    "verified": req.requirements_verified,
                })
    return JsonResponse({
        "programmes": matches,
        "notice": "Indicative matches only. Subject grades, programme-specific weighted points, institution cutoffs and vacancies require verification by the admissions team.",
    })


@require_http_methods(["GET", "POST"])
def student_signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = DepartmentStudentSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("campus_access:pending")
    return render(request, "campus_admissions_units/student_signup.html", {"form": form})


@login_required
@require_http_methods(["GET", "POST"])
def register_units(request):
    require_role(request, "STUDENT")
    record = (StudentProgramme.objects.select_related("programme")
              .filter(student=request.user, status=StudentProgramme.Status.ACTIVE).first())
    if not record:
        return render(request, "campus_admissions_units/student_units.html", {"record": None})
    placements = list(ProgrammeUnit.objects.filter(
        programme=record.programme, year=record.current_year, semester=record.current_semester,
    ).select_related("unit", "lms_course").order_by("unit__code"))
    previous = SemesterRegistration.objects.filter(
        student_programme=record, year=record.current_year, semester=record.current_semester,
    ).first()
    if request.method == "POST":
        if previous:
            messages.error(request, "This semester's unit registration was already submitted.")
            return redirect("campus_admissions_units:register_units")
        allowed = {str(p.pk): p for p in placements}
        raw_selected = request.POST.getlist("units")
        selected = set(raw_selected)
        if (not selected or len(selected) != len(raw_selected)
                or not selected.issubset(allowed)):
            messages.error(request, "Choose valid units from your current semester.")
        elif any(p.required and str(p.pk) not in selected for p in placements):
            messages.error(request, "Please include every required unit in this semester.")
        else:
            with transaction.atomic():
                # Lock this student's programme record to prevent simultaneous duplicate submissions.
                StudentProgramme.objects.select_for_update().get(pk=record.pk)
                if SemesterRegistration.objects.filter(
                    student_programme=record, year=record.current_year, semester=record.current_semester,
                ).exists():
                    messages.error(request, "This semester's registration was already received.")
                else:
                    registration = SemesterRegistration.objects.create(
                        student_programme=record, year=record.current_year, semester=record.current_semester,
                    )
                    RegisteredUnit.objects.bulk_create([
                        RegisteredUnit(registration=registration, placement=allowed[pk])
                        for pk in selected
                    ])
                    messages.success(request, "Your selected units were sent for lecturer approval.")
                    return redirect("campus_admissions_units:register_units")
    current = list(previous.units.select_related("placement__unit", "placement__lms_course").all()) if previous else []
    rows = []
    registered_by_id = {r.placement_id: r for r in current}
    for placement in placements:
        review = registered_by_id.get(placement.pk)
        rows.append({
            "placement": placement, "review": review,
            "lecturer": get_unit_lecturer(placement),
        })
    return render(request, "campus_admissions_units/student_units.html", {
        "record": record, "rows": rows, "registration": previous,
    })


@login_required
@require_GET
def lecturer_queue(request):
    require_role(request, "LECTURER")
    base = (RegisteredUnit.objects.select_related(
        "registration__student_programme__student", "registration__student_programme__programme",
        "placement__unit", "placement__lms_course__lecturer", "placement__review_assignment__lecturer",
    ).filter(
        Q(placement__review_assignment__lecturer=request.user)
        | Q(placement__review_assignment__isnull=True, placement__lms_course__lecturer=request.user),
        registration__student_programme__status=StudentProgramme.Status.ACTIVE,
    ).distinct())
    pending = base.filter(status=RegisteredUnit.Status.PENDING).order_by("registration__submitted_at", "id")
    reviewed = base.exclude(status=RegisteredUnit.Status.PENDING).order_by("-reviewed_at")[:20]
    return render(request, "campus_admissions_units/lecturer_queue.html", {
        "pending": pending, "reviewed": reviewed,
    })


@login_required
@require_POST
def lecturer_review(request, unit_id):
    require_role(request, "LECTURER")
    item = get_object_or_404(
        RegisteredUnit.objects.select_related("placement__lms_course__lecturer", "placement__unit"),
        pk=unit_id,
    )
    if get_unit_lecturer(item.placement) != request.user:
        raise PermissionDenied("You are not assigned to this unit")
    action = request.POST.get("decision")
    if action not in ("approve", "reject"):
        return HttpResponseBadRequest("Invalid decision")
    try:
        review_unit(item, request.user, approve=(action == "approve"), note=request.POST.get("note", ""))
        messages.success(request, "Unit request reviewed successfully.")
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect("campus_admissions_units:lecturer_queue")
