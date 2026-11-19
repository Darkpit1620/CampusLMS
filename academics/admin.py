from django.contrib import admin
from .models import Programme, Unit, ProgrammeUnit, StudentProgramme


class ProgrammeUnitInline(admin.TabularInline):
    model = ProgrammeUnit
    extra = 0
    fields = ("unit", "year", "semester", "required", "lms_course")
    show_change_link = True


@admin.register(Programme)
class ProgrammeAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "department", "duration_years", "is_active")
    list_filter = ("is_active", "duration_years")
    search_fields = ("code", "name", "department")
    inlines = (ProgrammeUnitInline,)


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = ("code", "title", "credits")
    search_fields = ("code", "title")


@admin.register(ProgrammeUnit)
class ProgrammeUnitAdmin(admin.ModelAdmin):
    list_display = ("programme", "unit", "year", "semester", "required", "lms_course")
    list_filter = ("programme", "year", "semester", "required")
    search_fields = ("programme__code", "programme__name", "unit__code", "unit__title")
    list_select_related = ("programme", "unit", "lms_course")


@admin.register(StudentProgramme)
class StudentProgrammeAdmin(admin.ModelAdmin):
    list_display = ("student", "programme", "current_year", "current_semester", "status", "intake_year")
    list_filter = ("programme", "current_year", "current_semester", "status")
    search_fields = ("student__username", "student__first_name", "student__last_name", "programme__code")
    list_select_related = ("student", "programme")
