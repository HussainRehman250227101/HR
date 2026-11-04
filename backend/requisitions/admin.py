from django.contrib import admin

from .models import Requisition


@admin.register(Requisition)
class RequisitionAdmin(admin.ModelAdmin):
    list_display = (
        "reference_code", "title", "department", "status",
        "employment_type", "created_by", "hiring_manager", "created_at",
    )
    list_filter = ("status", "department", "employment_type", "work_mode")
    search_fields = ("title", "department", "location", "description", "reference_code")
    readonly_fields = ("reference_code", "opened_at", "closed_at", "created_at", "updated_at")
    autocomplete_fields = ("created_by", "hiring_manager")
    date_hierarchy = "created_at"
