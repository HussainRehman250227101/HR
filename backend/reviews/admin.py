from django.contrib import admin

from .models import ShortlistReview


@admin.register(ShortlistReview)
class ShortlistReviewAdmin(admin.ModelAdmin):
    list_display = ("candidate", "decision", "score_override", "decided_by", "created_at")
    list_filter = ("decision", "created_at")
    search_fields = ("candidate__full_name", "candidate__email", "evaluation__public_id")
    readonly_fields = (
        "public_id", "candidate", "evaluation", "decision", "decision_reason",
        "score_override", "score_override_reason", "previous_candidate_status",
        "resulting_candidate_status", "decided_by", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
