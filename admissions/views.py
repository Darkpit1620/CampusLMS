from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_http_methods

from .forms import StudentRegistrationForm


@require_http_methods(["GET", "POST"])
def register_student(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    form = StudentRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("admissions:pending")

    return render(request, "admissions/register.html", {"form": form})


@require_GET
def registration_pending(request):
    return render(request, "admissions/pending.html")
