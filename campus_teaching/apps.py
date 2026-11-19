from django.apps import AppConfig


class CampusTeachingConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'campus_teaching'
    verbose_name = 'Teaching Units and Assignments'

    def ready(self):
        from . import signals  # noqa: F401
