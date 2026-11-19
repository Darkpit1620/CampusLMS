from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from .models import LecturerDepartmentPreference, LecturerUnitRequest


@admin.register(LecturerDepartmentPreference)
class LecturerDepartmentPreferenceAdmin(admin.ModelAdmin):
    list_display = ('lecturer', 'department', 'updated_at')
    list_filter = ('department',)
    search_fields = ('lecturer__username', 'lecturer__email', 'department')


@admin.register(LecturerUnitRequest)
class LecturerUnitRequestAdmin(admin.ModelAdmin):
    list_display = ('lecturer', 'department', 'placement', 'status', 'created_at')
    list_filter = ('status', 'placement__programme__department', 'placement__year', 'placement__semester')
    search_fields = ('lecturer__email', 'lecturer__username', 'placement__unit__title', 'placement__unit__code')
    readonly_fields = ('lecturer', 'placement', 'status', 'reviewed_by', 'review_note', 'created_at', 'reviewed_at')
    actions = ('approve_requests', 'reject_requests')
    list_select_related = ('lecturer', 'placement__programme', 'placement__unit')

    @admin.display(description='Department')
    def department(self, obj):
        return obj.placement.programme.department

    @admin.action(description='Approve selected teaching requests (approved lecturers only)')
    def approve_requests(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, 'Only superusers can approve teaching requests.', level=messages.ERROR)
            return
        approved = 0
        for item in queryset:
            try:
                if item.status != LecturerUnitRequest.Status.APPROVED:
                    item.approve(request.user)
                    approved += 1
            except ValidationError as exc:
                self.message_user(request, f'{item}: {exc}', level=messages.ERROR)
        if approved:
            self.message_user(request, f'Approved {approved} teaching request(s).', level=messages.SUCCESS)

    @admin.action(description='Reject selected pending teaching requests')
    def reject_requests(self, request, queryset):
        if not request.user.is_superuser:
            self.message_user(request, 'Only superusers can reject requests.', level=messages.ERROR)
            return
        rejected = 0
        for item in queryset:
            try:
                item.reject(request.user, note='Please contact your department for details.')
                rejected += 1
            except ValidationError as exc:
                self.message_user(request, f'{item}: {exc}', level=messages.ERROR)
        if rejected:
            self.message_user(request, f'Rejected {rejected} request(s).', level=messages.SUCCESS)
