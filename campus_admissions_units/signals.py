from django.db.models.signals import post_save
from django.dispatch import receiver
from admissions.models import StudentAdmission
from .services import place_approved_applicant


@receiver(post_save, sender=StudentAdmission, dispatch_uid="campus_admissions_units_place_approved_applicant")
def applicant_admission_updated(sender, instance, **kwargs):
    if instance.status == StudentAdmission.Status.APPROVED:
        place_approved_applicant(instance)
