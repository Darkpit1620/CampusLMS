from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_GET, require_http_methods
from django.contrib.auth.decorators import login_required
from admissions.forms import CampusAuthenticationForm


from .models import EmployeeApplication


class UniversityLoginForm(CampusAuthenticationForm):
    """Accept approved admission numbers, employee IDs, and legacy usernames."""
    def clean(self):
        identifier = (self.cleaned_data.get("username") or "").strip()
        if identifier:
            application = (
                EmployeeApplication.objects.select_related("user")
                .filter(
                    registration_number__iexact=identifier,
                    status=EmployeeApplication.Status.APPROVED,
                ).first()
            )
            if application:
                self.cleaned_data["username"] = application.user.get_username()
            elif "@" in identifier:
                self.cleaned_data["username"] = identifier.lower()
        return super().clean()

from .forms import EmployeeSignupForm, InternationalStudentForm


@require_GET
def access_home(request):
    return render(request, "campus_access/home.html")


@require_http_methods(["GET", "POST"])
def student_signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = InternationalStudentForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("campus_access:pending")
    return render(request, "campus_access/signup.html", {
        "form": form, "role_title": "Student",
        "intro": "Apply to join CampusLMS. Your admission number is issued after approval.",
    })


@require_http_methods(["GET", "POST"])
def employee_signup(request, role):
    requested_role = {"lecturer": "LECTURER", "staff": "STAFF"}.get(role)
    if not requested_role:
        raise PermissionDenied("Unknown account type")
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = EmployeeSignupForm(request.POST or None, requested_role=requested_role)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("campus_access:pending")
    return render(request, "campus_access/signup.html", {
        "form": form,
        "role_title": "Lecturer" if requested_role == "LECTURER" else "University Staff",
        "intro": "Your university account will remain pending until an administrator approves it.",
    })


@require_GET
def pending(request):
    return render(request, "campus_access/pending.html")


class RoleLoginView(LoginView):
    template_name = "campus_access/login.html"
    authentication_form = UniversityLoginForm
    redirect_authenticated_user = False
    role_titles = {
        "student": "Student",
        "lecturer": "Lecturer",
        "staff": "University Staff",
    }

    def dispatch(self, request, *args, **kwargs):
        if self.kwargs.get("role") not in self.role_titles:
            raise PermissionDenied("Unknown login role")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        data = super().get_context_data(**kwargs)
        data["role_title"] = self.role_titles[self.kwargs["role"]]
        data["role_key"] = self.kwargs["role"]
        return data

    def form_valid(self, form):
        person = form.get_user()
        required = self.kwargs["role"].upper()
        if person.role != required or person.is_superuser or person.is_staff:
            form.add_error(None, "This account belongs to a different portal.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        if self.kwargs["role"] == "staff":
            return str(reverse_lazy("campus_access:staff_workspace"))
        return str(reverse_lazy("dashboard"))


@login_required
@require_GET
def staff_workspace(request):
    if request.user.role != "STAFF" or request.user.is_staff or request.user.is_superuser:
        raise PermissionDenied("University staff only")
    return render(request, "campus_access/staff_workspace.html")
