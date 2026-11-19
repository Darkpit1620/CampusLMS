"""Issue at most one hostel invoice when staff allocates a room."""
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import HostelAllocation, HostelRequest, FeeCharge


@receiver(post_save, sender=HostelAllocation)
def invoice_new_hostel_allocation(sender, instance, created, **kwargs):
    if created and instance.room.semester_fee > 0:
        FeeCharge.objects.get_or_create(
            hostel_allocation=instance,
            defaults={
                "student": instance.student,
                "category": FeeCharge.Category.HOSTEL,
                "description": f"Accommodation: {instance.room.hostel.name} / {instance.room.number}",
                "amount": instance.room.semester_fee,
                "academic_year": instance.academic_year,
                "semester": instance.semester,
            },
        )
    if instance.status == HostelAllocation.Status.ACTIVE:
        HostelRequest.objects.filter(
            student=instance.student, academic_year=instance.academic_year,
            semester=instance.semester, status=HostelRequest.Status.PENDING,
        ).update(status=HostelRequest.Status.ALLOCATED)
