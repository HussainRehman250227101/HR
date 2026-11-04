from django.contrib import admin

from .models import Candidate,CandidateEvent,ResumeDocument


class ResumeDocumentInline(admin.TabularInline):
    model=ResumeDocument
    extra=0
    fields=("public_id","original_filename","file_size","processing_status","error_code","created_at")
    readonly_fields=fields
    can_delete=False


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display=("public_id","full_name","email","requisition","current_status","contact_consent_status","created_at")
    list_filter=("current_status","contact_consent_status","requisition")
    search_fields=("full_name","email","phone","public_id")
    readonly_fields=("public_id","created_at","updated_at")
    inlines=(ResumeDocumentInline,)


@admin.register(ResumeDocument)
class ResumeDocumentAdmin(admin.ModelAdmin):
    list_display=("public_id","original_filename","candidate","processing_status","file_size","created_at","processed_at")
    list_filter=("processing_status","content_type")
    search_fields=("original_filename","candidate__full_name","candidate__email")
    readonly_fields=("public_id","sha256","extracted_text","extraction_metadata","created_at","processed_at")


@admin.register(CandidateEvent)
class CandidateEventAdmin(admin.ModelAdmin):
    list_display=("candidate","event_type","actor","created_at")
    list_filter=("event_type","created_at")
    readonly_fields=("candidate","actor","event_type","details","created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
