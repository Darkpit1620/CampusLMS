from decimal import Decimal
from django import forms
from django.db import transaction
from django.utils import timezone
from academics.models import Programme
from campus_access.forms import InternationalStudentForm
from .models import GRADE_CHOICES, ProgrammeApplication
from .services import preliminary_match


class ApplicantSignupForm(InternationalStudentForm):
    kcse_mean_grade = forms.ChoiceField(label="KCSE mean grade", choices=[("", "Select KCSE grade")] + GRADE_CHOICES)
    reported_cluster_points = forms.DecimalField(
        label="Your estimated programme cluster points (0–48)", max_digits=5,
        decimal_places=2, min_value=Decimal("0"), max_value=Decimal("48"),
        help_text="Use your applicable weighted cluster points. Scores vary by programme cluster."
    )
    programme = forms.ModelChoiceField(
        label="Preferred university programme",
        queryset=Programme.objects.none(),
        empty_label="Enter grade and score to see programme choices",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["programme"].queryset = Programme.objects.filter(is_active=True).select_related("admission_requirement")
        self.order_fields([
            "first_name", "last_name", "email", "phone_country", "phone_number", "date_of_birth",
            "kcse_mean_grade", "reported_cluster_points", "programme", "password1", "password2",
        ])
        self.fields["programme"].widget.attrs["data-programme-selector"] = "1"

    def clean(self):
        values = super().clean()
        programme = values.get("programme")
        grade = values.get("kcse_mean_grade")
        points = values.get("reported_cluster_points")
        if programme and grade and points is not None and not preliminary_match(programme, grade, points):
            self.add_error("programme", "This programme is outside your currently displayed score range. Check your details or choose another programme.")
        return values

    @transaction.atomic
    def save(self):
        admission = super().save()
        ProgrammeApplication.objects.create(
            admission=admission,
            programme=self.cleaned_data["programme"],
            kcse_mean_grade=self.cleaned_data["kcse_mean_grade"],
            reported_cluster_points=self.cleaned_data["reported_cluster_points"],
        )
        return admission
