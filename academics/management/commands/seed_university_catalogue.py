"""Safely populate the sample multi-programme university catalogue.

Run: python manage.py seed_university_catalogue
Repeat-safe: get_or_create only, never clears/overwrites existing data.
"""
import json
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from academics.models import Programme, ProgrammeUnit, Unit
from courses.models import Course

DATA = Path(__file__).resolve().parents[2] / "data" / "university_catalogue.json"


class Command(BaseCommand):
    help = "Create 16 sample academic programmes and 840 unit placements (safe to run again)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Validate and preview without writing to the database.",
        )

    def handle(self, *args, **options):
        if not DATA.is_file():
            raise CommandError(f"Missing academic catalogue data file: {DATA}")
        try:
            payload = json.loads(DATA.read_text(encoding="utf-8"))
        except (ValueError, OSError) as exc:
            raise CommandError(f"Cannot read catalogue: {exc}") from exc
        programmes = payload.get("programmes", [])
        if not programmes:
            raise CommandError("Catalogue contains no programmes; nothing changed.")

        existing_codes = set()
        existing_unit_codes = set()
        placements = 0
        for prog in programmes:
            if prog["code"] in existing_codes:
                raise CommandError(f"Duplicate programme code {prog['code']} in source data")
            existing_codes.add(prog["code"])
            counts = Counter((u["year"], u["semester"]) for u in prog["units"])
            expected = {(y, s) for y in range(1, prog["duration_years"] + 1) for s in range(1, 4)}
            if set(counts) != expected or any(v != 5 for v in counts.values()):
                raise CommandError(f"Programme {prog['code']} must have five units in every term")
            for unit in prog["units"]:
                code = unit["code"]
                if code in existing_unit_codes:
                    raise CommandError(f"Duplicate unit code in source data: {code}")
                existing_unit_codes.add(code)
                if len(code) > 24 or len(unit["title"]) > 200:
                    raise CommandError(f"Invalid unit code or title for {code}")
                placements += 1

        # Protect any existing records with the same code but different meaning.
        for prog in programmes:
            existing = Programme.objects.filter(code=prog["code"]).first()
            if existing and existing.duration_years < prog["duration_years"]:
                raise CommandError(
                    f"Existing programme {existing.code} lasts {existing.duration_years} year(s); "
                    "catalogue needs a longer duration. Fix in Admin, then retry. No data changed."
                )
        # Chunk the lookup to support SQLite's parameter limits.
        mismatches = []
        codes = sorted(existing_unit_codes)
        desired_titles = {u["code"]: u["title"] for p in programmes for u in p["units"]}
        for i in range(0, len(codes), 400):
            for existing in Unit.objects.filter(code__in=codes[i:i+400]).only("code", "title"):
                if existing.title.strip().casefold() != desired_titles[existing.code].strip().casefold():
                    mismatches.append(existing.code)
        if mismatches:
            raise CommandError(
                "Existing units have the same codes but different titles: "
                + ", ".join(mismatches[:12])
                + ". No changes made. Review those units with your administrator."
            )

        self.stdout.write(
            f"Validated {len(programmes)} programmes and {placements} unit placements "
            "(five units in every semester)."
        )
        if options["dry_run"]:
            self.stdout.write("Dry run: no records created or modified.")
            return

        created_programmes = created_units = created_placements = 0
        link_count = 0
        linked_course = Course.objects.filter(code="CSC101").first()
        with transaction.atomic():
            for prog in programmes:
                programme, created = Programme.objects.get_or_create(
                    code=prog["code"],
                    defaults={
                        "name": prog["name"],
                        "department": prog["department"],
                        "duration_years": prog["duration_years"],
                        "description": prog["description"],
                        "is_active": True,
                    },
                )
                created_programmes += int(created)
                for entry in prog["units"]:
                    unit, was_new = Unit.objects.get_or_create(
                        code=entry["code"],
                        defaults={
                            "title": entry["title"],
                            "credits": entry["credits"],
                            "description": "Illustrative academic unit. Review before official use.",
                        },
                    )
                    created_units += int(was_new)
                    should_link = (
                        prog["code"] == "BSC-CS"
                        and entry["code"] == "CSC101"
                        and linked_course is not None
                    )
                    placement, was_new = ProgrammeUnit.objects.get_or_create(
                        programme=programme,
                        unit=unit,
                        year=entry["year"],
                        semester=entry["semester"],
                        defaults={
                            "required": entry["required"],
                            "lms_course": linked_course if should_link else None,
                        },
                    )
                    created_placements += int(was_new)
                    # Link existing CSC101 only if no course was linked previously.
                    if should_link and placement.lms_course_id is None:
                        placement.lms_course = linked_course
                        placement.save(update_fields=["lms_course"])
                        link_count += 1
        self.stdout.write(self.style.SUCCESS(
            f"Sample catalogue ready. New programmes: {created_programmes}; "
            f"new units: {created_units}; new curriculum placements: {created_placements}; "
            f"CSC101 links added: {link_count}."
        ))
        self.stdout.write(
            "Existing users, enrolments, grades, submissions and teaching courses were not changed."
        )
        self.stdout.write(
            "NOTE: Illustrative curricula only. Admin must review programme/unit names "
            "and assign students/teaching courses before real academic use."
        )
