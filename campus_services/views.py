from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods
from academics.models import StudentProgramme
from .models import (FeePayment, HostelAllocation, HostelRequest,
                     GraduationApplication)
from .services import financial_statement, graduation_readiness


def student_only(request):
    if (request.user.role != "STUDENT" or request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Students can only view their own campus records.")


@login_required
@require_GET
def student_hub(request):
    student_only(request)
    statement = financial_statement(request.user)
    readiness = graduation_readiness(request.user)
    room = HostelAllocation.objects.filter(student=request.user, status="ACTIVE").select_related("room__hostel").order_by("-academic_year", "-semester").first()
    return render(request, "campus_services/student_hub.html", {
        "statement": statement, "readiness": readiness, "room": room,
    })


@login_required
@require_GET
def finances(request):
    student_only(request)
    statement = financial_statement(request.user)
    payments = FeePayment.objects.filter(charge__student=request.user).select_related("charge").order_by("-received_on", "-id")
    return render(request, "campus_services/finances.html", {
        "statement": statement, "payments": payments,
    })


@login_required
@require_http_methods(["GET", "POST"])
def accommodation(request):
    student_only(request)
    record = StudentProgramme.objects.filter(student=request.user).first()
    year = timezone.localdate().year
    semester = record.current_semester if record else None
    if request.method == "POST":
        if not record or record.status != StudentProgramme.Status.ACTIVE:
            messages.error(request, "An active university programme is needed before requesting accommodation.")
        elif HostelAllocation.objects.filter(student=request.user, academic_year=year, semester=semester).exists():
            messages.info(request, "You already have a hostel allocation for the current semester.")
        else:
            try:
                with transaction.atomic():
                    _, created = HostelRequest.objects.get_or_create(
                        student=request.user, academic_year=year, semester=semester)
                messages.success(request, "Hostel request submitted." if created else "Your hostel request already exists.")
            except IntegrityError:
                messages.info(request, "A hostel request for this semester already exists.")
        return redirect("campus_services:accommodation")
    allocations = HostelAllocation.objects.filter(student=request.user).select_related("room__hostel").order_by("-academic_year", "-semester")
    requests = HostelRequest.objects.filter(student=request.user).order_by("-submitted_at")
    can_request = bool(record and record.status == StudentProgramme.Status.ACTIVE and semester and not
        HostelRequest.objects.filter(student=request.user, academic_year=year, semester=semester).exists() and not
        HostelAllocation.objects.filter(student=request.user, academic_year=year, semester=semester).exists())
    return render(request, "campus_services/accommodation.html", {
        "allocations": allocations, "requests": requests, "can_request": can_request,
        "record": record,
    })


@login_required
@require_http_methods(["GET", "POST"])
def graduation(request):
    student_only(request)
    ready = graduation_readiness(request.user)
    application = GraduationApplication.objects.filter(student=request.user).first()
    if request.method == "POST":
        if application:
            messages.info(request, "Your graduation request is already recorded. Contact the registrar for corrections.")
        elif not ready["eligible"]:
            messages.error(request, "You cannot apply until all academic and clearance requirements are met.")
        else:
            try:
                with transaction.atomic():
                    GraduationApplication.objects.get_or_create(student=request.user)
                messages.success(request, "Your graduation application was sent to the registrar.")
            except IntegrityError:
                messages.info(request, "Your graduation request already exists.")
        return redirect("campus_services:graduation")
    return render(request, "campus_services/graduation.html", {
        "ready": ready, "application": application,
    })
