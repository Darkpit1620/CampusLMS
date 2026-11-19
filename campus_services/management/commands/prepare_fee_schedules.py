from decimal import Decimal
from django.core.management.base import BaseCommand
from academics.models import Programme
from campus_services.models import FeeStructure


class Command(BaseCommand):
    help = "Create inactive zero-value fee schedule placeholders for each programme semester; NEVER bill students."

    def handle(self, *args, **options):
        created = 0
        for programme in Programme.objects.all():
            for year in range(1, programme.duration_years + 1):
                for semester in (1, 2, 3):
                    _, new = FeeStructure.objects.get_or_create(
                        programme=programme, year=year, semester=semester,
                        defaults={
                            "tuition": Decimal("0.00"),
                            "other_fees": Decimal("0.00"),
                            "is_active": False,
                            "note": "PLACEHOLDER: Enter approved fees and activate before billing students.",
                        },
                    )
                    created += int(new)
        self.stdout.write(self.style.SUCCESS(
            f"Prepared {created} new inactive fee schedule placeholders. No students were charged."
        ))
