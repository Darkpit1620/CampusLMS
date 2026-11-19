import uuid

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from .models import StudentAdmission


class StudentRegistrationForm(forms.Form):
    first_name = forms.CharField(max_length=150, label="First name")
    last_name = forms.CharField(max_length=150, label="Last name")
    email = forms.EmailField(label="Email address")
    phone_number = forms.CharField(
        max_length=25,
        label="Phone number",
        validators=[RegexValidator(
            regex=r"^\+?[0-9][0-9\s-]{7,19}$",
            message="Enter a valid phone number, such as +254712345678.",
        )],
    )
    date_of_birth = forms.DateField(
        label="Date of birth",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    password1 = forms.CharField(
        label="Create password", widget=forms.PasswordInput
    )
    password2 = forms.CharField(
        label="Confirm password", widget=forms.PasswordInput
    )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_date_of_birth(self):
        dob = self.cleaned_data["date_of_birth"]
        if dob >= timezone.localdate():
            raise forms.ValidationError("Enter a date of birth in the past.")
        return dob

    def clean(self):
        data = super().clean()
        first = data.get("password1")
        second = data.get("password2")
        if first and second and first != second:
            self.add_error("password2", "The passwords do not match.")
        if first:
            candidate = User(
                first_name=data.get("first_name", ""),
                last_name=data.get("last_name", ""),
                email=data.get("email", ""),
            )
            try:
                validate_password(first, user=candidate)
            except ValidationError as error:
                self.add_error("password1", error)
        return data

    @transaction.atomic
    def save(self):
        if not self.is_valid():
            raise ValueError("Cannot save an invalid registration form")
        user = User.objects.create_user(
            username="student_" + uuid.uuid4().hex,
            password=self.cleaned_data["password1"],
            first_name=self.cleaned_data["first_name"].strip(),
            last_name=self.cleaned_data["last_name"].strip(),
            email=self.cleaned_data["email"],
            role=User.Role.STUDENT,
            is_active=False,
            is_staff=False,
            is_superuser=False,
        )
        return StudentAdmission.objects.create(
            user=user,
            phone_number=self.cleaned_data["phone_number"].strip(),
            date_of_birth=self.cleaned_data["date_of_birth"],
        )


class CampusAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        label="Admission number (student) or username (staff)",
        widget=forms.TextInput(attrs={"autocomplete": "username"}),
    )

    def clean(self):
        identifier = (self.cleaned_data.get("username") or "").strip()
        admission = None
        if identifier:
            admission = (
                StudentAdmission.objects.select_related("user")
                .filter(
                    admission_number__iexact=identifier,
                    status=StudentAdmission.Status.APPROVED,
                )
                .first()
            )
            if admission:
                self.cleaned_data["username"] = admission.user.get_username()

        data = super().clean()
        logged_in_user = self.get_user()
        if logged_in_user and logged_in_user.role == "STUDENT":
            if not admission or admission.user_id != logged_in_user.pk:
                raise self.get_invalid_login_error()
        return data
