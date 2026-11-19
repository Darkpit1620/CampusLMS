
from django import forms
from django.utils import timezone

from .models import Assignment, Submission, Grade


class AssignmentForm(forms.ModelForm):

    due_at = forms.DateTimeField(
        label="Submission Deadline",
        widget=forms.DateTimeInput(
            attrs={"type": "datetime-local"},
            format="%Y-%m-%dT%H:%M",
        ),
        input_formats=["%Y-%m-%dT%H:%M"],
    )

    class Meta:
        model = Assignment

        fields = [
            "title",
            "instructions",
            "due_at",
            "max_marks",
        ]

        widgets = {
            "title": forms.TextInput(
                attrs={
                    "placeholder": "Enter assignment title"
                }
            ),
            "instructions": forms.Textarea(
                attrs={
                    "rows": 5,
                    "placeholder": "Enter assignment instructions"
                }
            ),
        }

    def clean_due_at(self):
        due_at = self.cleaned_data["due_at"]

        if due_at <= timezone.now():
            raise forms.ValidationError(
                "The deadline must be in the future."
            )

        return due_at


class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ["file"]

        widgets = {
            "file": forms.ClearableFileInput(
                attrs={"accept": ".pdf,.docx"}
            ),
        }


class GradeForm(forms.ModelForm):
    class Meta:
        model = Grade
        fields = ["marks", "feedback"]

        widgets = {
            "feedback": forms.Textarea(
                attrs={"rows": 5}
            ),
        }

    def __init__(self, *args, submission, **kwargs):
        super().__init__(*args, **kwargs)
        self.submission = submission

        self.fields["marks"].widget.attrs["max"] = (
            submission.assignment.max_marks
        )

    def clean_marks(self):
        marks = self.cleaned_data["marks"]

        if marks > self.submission.assignment.max_marks:
            raise forms.ValidationError(
                "Marks exceed the assignment maximum."
            )

        return marks
