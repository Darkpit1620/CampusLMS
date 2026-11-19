"""Create course links after explicit administrator assignment, never after signup."""
import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from campus_admissions_units.models import UnitLecturerAssignment
from .services import ensure_teaching_course

logger = logging.getLogger(__name__)


@receiver(post_save, sender=UnitLecturerAssignment, dispatch_uid='campus_teaching_link_course')
def link_approved_unit(sender, instance, **kwargs):
    try:
        ensure_teaching_course(instance.placement, instance.lecturer)
    except Exception as error:
        # Preserve an administrator's existing records if course creation is
        # incompatible with a locally customized Course model. The approval
        # workflow itself validates the link and rolls back on failure;
        # manual admin assignments can be repaired via sync_teaching_courses.
        logger.error('Approved unit %s could not be linked to LMS Course: %s', instance.placement_id, error)
