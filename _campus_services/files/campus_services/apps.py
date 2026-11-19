from django.apps import AppConfig


class CampusServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "campus_services"
    verbose_name = "Student Finance, Accommodation & Graduation"

    def ready(self):
        from . import signals  # noqa: F401
