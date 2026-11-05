from django.contrib import admin

from .models import WorkflowRun


@admin.register(WorkflowRun)
class WorkflowRunAdmin(admin.ModelAdmin):
    list_display = ("public_id", "candidate", "status", "current_step", "created_by", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("candidate__full_name", "candidate__email", "public_id", "thread_id")
    readonly_fields = (
        "public_id", "thread_id", "candidate", "resume_document", "evaluation",
        "status", "current_step", "error_code", "error_message",
        "state_summary", "created_by", "started_at", "completed_at",
        "created_at", "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
