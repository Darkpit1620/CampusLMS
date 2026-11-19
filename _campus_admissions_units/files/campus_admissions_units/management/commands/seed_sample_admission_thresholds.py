"""Seeds labelled ILLUSTRATIVE score thresholds, not real KUCCPS programme cutoffs."""
from decimal import Decimal
from django.core.management.base import BaseCommand
from academics.models import Programme
from campus_admissions_units.models import ProgrammeRequirement


EXAMPLES = {
    "BENG-EEE": ("40.00", "C+"),
    "BSC-NUR": ("38.00", "C+"),
    "BSC-CS": ("32.00", "C+"),
    "BSC-SE": ("32.00", "C+"),
    "BSC-DS": ("32.00", "C+"),
    "BSC-IT": ("27.00", "C+"),
    "BCOM": ("27.00", "C+"),
    "BBA": ("25.00", "C+"),
    "BED-SCI": ("30.00", "C+"),
    "BED-ART": ("26.00", "C+"),
    "BSC-AGR": ("25.00", "C+"),
    "BSC-ENV": ("25.00", "C+"),
    "DIP-IT": ("0", "C-"),
    "DIP-BM": ("0", "C-"),
    "DIP-HM": ("0", "C-"),
    "DIP-CH": ("0", "C-"),
}


class Command(BaseCommand):
    help = "Populate explicitly unverified example thresholds for the demo catalogue (never overwrite existing rules)."

    def handle(self, *args, **options):
        created = 0
        for programme in Programme.objects.all():
            if programme.code in EXAMPLES:
                pts, grade = EXAMPLES[programme.code]
            elif programme.code.startswith("DIP-"):
                pts, grade = "0", "C-"
            else:
                pts, grade = "30", "C+"
            _obj, was_created = ProgrammeRequirement.objects.get_or_create(
                programme=programme,
                defaults={
                    "minimum_cluster_points": Decimal(pts),
                    "minimum_mean_grade": grade,
                    "requirements_verified": False,
                    "applications_open": True,
                    "source_notes": "ILLUSTRATIVE demonstration values; NOT official KUCCPS cutoffs. Administrator verification required.",
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(
            f"Created {created} SAMPLE admission rule(s). Existing rules were left unchanged. "
            "Confirm institution-specific current KUCCPS and subject requirements before official admissions."
        ))
