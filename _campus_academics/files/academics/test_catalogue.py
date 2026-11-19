"""Catalogue installation checks on a disposable Django test database."""
from django.core.management import call_command
from django.test import TestCase
from academics.models import Programme, ProgrammeUnit, Unit


class CompleteCatalogueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_university_catalogue", verbosity=0)

    def test_programmes_and_placements(self):
        for code in ("BSC-CS", "BSC-IT", "BCOM", "BSC-NUR", "BENG-EEE", "DIP-IT", "DIP-HM"):
            self.assertTrue(Programme.objects.filter(code=code).exists(), code)
        self.assertEqual(Programme.objects.count(), 16)
        self.assertEqual(Unit.objects.count(), 840)
        self.assertEqual(ProgrammeUnit.objects.count(), 840)

    def test_every_term_has_five_units(self):
        for programme in Programme.objects.all():
            self.assertEqual(
                ProgrammeUnit.objects.filter(programme=programme).count(),
                programme.duration_years * 3 * 5,
            )
            for year in range(1, programme.duration_years+1):
                for semester in range(1, 4):
                    self.assertEqual(
                        ProgrammeUnit.objects.filter(
                            programme=programme, year=year, semester=semester
                        ).count(), 5
                    )

    def test_repeat_seed_does_not_duplicate_records(self):
        call_command("seed_university_catalogue", verbosity=0)
        self.assertEqual(Programme.objects.count(), 16)
        self.assertEqual(Unit.objects.count(), 840)
        self.assertEqual(ProgrammeUnit.objects.count(), 840)
