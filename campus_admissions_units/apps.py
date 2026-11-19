from django.apps import AppConfig


class CampusAdmissionsUnitsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "campus_admissions_units"
    verbose_name = "Admissions and Unit Registration"

    def ready(self):
        from . import signals  # noqa: F401
