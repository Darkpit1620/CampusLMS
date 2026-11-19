from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from admissions.forms import StudentRegistrationForm
from .models import EmployeeApplication, StudentCountry
from .phone import country_choices, normalize_phone


COUNTRY_OPTIONS = country_choices()


class InternationalStudentForm(StudentRegistrationForm):
    """Extend current registration without changing the StudentAdmission model."""
    phone_country = forms.ChoiceField(
        label="Country / dialing code",
        choices=COUNTRY_OPTIONS,
        initial="KE",
        widget=forms.Select(attrs={"class": "access-input"}),
    )
    phone_number = forms.CharField(
        max_length=30,
        label="Phone number (without country code)",
        widget=forms.TextInput(attrs={
            "type": "tel", "placeholder": "712345678", "class": "access-input",
            "autocomplete": "tel-national",
        }),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.order_fields([
            "first_name", "last_name", "email", "phone_country",
            "phone_number", "date_of_birth", "password1", "password2",
        ])

    def clean(self):
        data = super().clean()
        country = data.get("phone_country")
        local = data.get("phone_number")
        if country and local:
            try:
                data["phone_number"] = normalize_phone(local, country)
            except forms.ValidationError as exc:
                self.add_error("phone_number", exc)
        return data

    @transaction.atomic
    def save(self):
        admission = super().save()
        StudentCountry.objects.create(
            admission=admission,
            country=self.cleaned_data["phone_country"],
        )
        return admission


class EmployeeSignupForm(forms.Form):
    first_name = forms.CharField(max_length=150)
    last_name = forms.CharField(max_length=150)
    email = forms.EmailField()
    phone_country = forms.ChoiceField(
        label="Country / dialing code", choices=COUNTRY_OPTIONS, initial="KE"
    )
    phone_number = forms.CharField(
        max_length=30,
        label="Phone number (without country code)",
        widget=forms.TextInput(attrs={"type": "tel", "placeholder": "712345678"}),
    )
    date_of_birth = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"})
    )
    department = forms.CharField(max_length=120)
    job_title = forms.CharField(max_length=120, required=False)
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm password", widget=forms.PasswordInput)

    def __init__(self, *args, requested_role, **kwargs):
        if requested_role not in ("LECTURER", "STAFF"):
            raise ValueError("Invalid requested role")
        self.requested_role = requested_role
        super().__init__(*args, **kwargs)
        if requested_role == "LECTURER":
            self.fields["job_title"].label = "Academic title (optional)"
        else:
            self.fields["job_title"].label = "Job title (optional)"

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if len(email) > 150:
            raise forms.ValidationError("Email address is too long for login.")
        if User.objects.filter(email__iexact=email).exists() or User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_date_of_birth(self):
        dob = self.cleaned_data["date_of_birth"]
        if dob >= timezone.localdate():
            raise forms.ValidationError("Enter a date of birth in the past.")
        return dob

    def clean(self):
        data = super().clean()
        first, second = data.get("password1"), data.get("password2")
        if first and first != second:
            self.add_error("password2", "Passwords must match.")
        if first:
            sample = User(
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                email=data.get("email", ""),
            )
            try:
                validate_password(first, user=sample)
            except ValidationError as exc:
                self.add_error("password1", exc)
        country, local = data.get("phone_country"), data.get("phone_number")
        if country and local:
            try:
                data["phone_number"] = normalize_phone(local, country)
            except forms.ValidationError as exc:
                self.add_error("phone_number", exc)
        return data

    @transaction.atomic
    def save(self):
        if not self.is_valid():
            raise ValueError("Invalid application")
        data = self.cleaned_data
        user = User.objects.create_user(
            username=data["email"],
            password=data["password1"],
            first_name=data["first_name"].strip(),
            last_name=data["last_name"].strip(),
            email=data["email"],
            role=self.requested_role,
            is_active=False,
            is_staff=False,
            is_superuser=False,
        )
        return EmployeeApplication.objects.create(
            user=user,
            requested_role=self.requested_role,
            phone_number=data["phone_number"],
            country=data["phone_country"],
            date_of_birth=data["date_of_birth"],
            department=data["department"].strip(),
            job_title=data.get("job_title", "").strip(),
        )
