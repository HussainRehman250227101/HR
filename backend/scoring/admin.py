from django.contrib import admin

from .models import ResumeEvaluation, ScoringRubric


@admin.register(ScoringRubric)
class ScoringRubricAdmin(admin.ModelAdmin):
    list_display = ("requisition", "name", "version", "is_active", "updated_by", "updated_at")
    list_filter = ("is_active",)
    readonly_fields = ("public_id", "requisition", "name", "weights", "version", "is_active", "notes", "updated_by", "created_at", "updated_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ResumeEvaluation)
class ResumeEvaluationAdmin(admin.ModelAdmin):
    list_display = ("candidate", "requisition", "version", "overall_score", "assessed_weight", "confidence_level", "recommendation_for_human_review", "created_at")
    list_filter = ("confidence_level", "recommendation_for_human_review", "provider")
    search_fields = ("candidate__full_name", "candidate__email", "requisition__title")
    readonly_fields = (
        "public_id", "candidate", "requisition", "resume_document", "rubric",
        "version", "overall_score", "assessed_weight", "criterion_scores",
        "evidence", "missing_or_unclear_items", "parsing_warnings",
        "confidence_level", "recommendation_for_human_review",
        "overall_assessment", "provider", "model_version", "prompt_version",
        "input_sha256", "created_by", "created_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
