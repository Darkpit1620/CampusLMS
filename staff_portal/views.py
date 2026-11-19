from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from campus_access.models import EmployeeApplication
from .forms import StaffSignupForm
from .models import StaffCategory, StaffDepartment, StaffProfile


def _department_data():
    return list(StaffDepartment.objects.filter(is_active=True).values(
        "name", "category", "description"
    ).order_by("category", "name"))


@require_http_methods(["GET", "POST"])
def staff_signup(request):
    if request.user.is_authenticated:
        return redirect("campus_access:staff_workspace" if request.user.role == "STAFF" else "dashboard")
    form = StaffSignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("campus_access:pending")
    return render(request, "staff_portal/signup.html", {
        "form": form,
        "department_catalogue": _department_data(),
    })


@login_required
@require_GET
def staff_dashboard(request):
    person = request.user
    if person.role != "STAFF" or not person.is_active or person.is_superuser:
        raise PermissionDenied("This page is for approved university staff accounts.")
    application = EmployeeApplication.objects.filter(
        user=person, requested_role="STAFF",
    ).first()
    profile = None
    if application:
        profile = StaffProfile.objects.select_related("department").filter(
            application=application
        ).first()
    departments = StaffDepartment.objects.filter(is_active=True)
    return render(request, "staff_portal/dashboard.html", {
        "application": application,
        "profile": profile,
        "departments_count": departments.count(),
        "teaching_support_count": departments.filter(category=StaffCategory.TEACHING_SUPPORT).count(),
        "non_teaching_count": departments.filter(category=StaffCategory.NON_TEACHING).count(),
    })


@login_required
@require_GET
def staff_departments(request):
    if request.user.role != "STAFF" or not request.user.is_active or request.user.is_superuser:
        raise PermissionDenied("University staff only")
    return render(request, "staff_portal/departments.html", {
        "teaching_support": StaffDepartment.objects.filter(
            is_active=True, category=StaffCategory.TEACHING_SUPPORT
        ),
        "non_teaching": StaffDepartment.objects.filter(
            is_active=True, category=StaffCategory.NON_TEACHING
        ),
    })
