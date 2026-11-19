from django.core.management.base import BaseCommand, CommandError
from campus_admissions_units.models import UnitLecturerAssignment
from campus_teaching.services import ensure_teaching_course


class Command(BaseCommand):
    help = 'Link existing administrator-approved unit assignments to LMS teaching courses without replacing existing data.'

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true')

    def handle(self, *args, **kwargs):
        dry_run = kwargs['dry_run']
        assignments = UnitLecturerAssignment.objects.select_related(
            'lecturer', 'placement__unit', 'placement__programme', 'placement__lms_course'
        ).order_by('placement_id')
        created_or_linked = 0
        skipped = 0
        errors = []
        for item in assignments:
            placement = item.placement
            if placement.lms_course_id and placement.lms_course.lecturer_id == item.lecturer_id:
                skipped += 1
                continue
            if dry_run:
                self.stdout.write(f'WOULD LINK {placement} -> {item.lecturer.get_username()}')
                continue
            try:
                course = ensure_teaching_course(placement, item.lecturer)
                created_or_linked += 1
                self.stdout.write(self.style.SUCCESS(f'LINKED {placement.unit.code} to {course.code}'))
            except Exception as error:
                errors.append(f'{placement} -> {item.lecturer.get_username()}: {error}')
        if dry_run:
            self.stdout.write(f'Dry run done. {skipped} already linked.')
            return
        self.stdout.write(self.style.SUCCESS(f'{created_or_linked} linked, {skipped} already linked, {len(errors)} need administrator review.'))
        for error in errors:
            self.stderr.write('NEEDS REVIEW: ' + error)
        if errors:
            raise CommandError(f'{len(errors)} approved unit(s) need administrator review before this upgrade can be considered complete.')
