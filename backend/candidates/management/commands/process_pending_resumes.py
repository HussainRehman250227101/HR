"""Process pending resume extraction work from a separate worker process."""

from django.core.management.base import BaseCommand,CommandError
from candidates.models import ResumeDocument,ResumeProcessingStatus
from candidates.services.processing import process_resume_document


class Command(BaseCommand):
    help="Extract text from pending PDF/DOCX resumes."

    def add_arguments(self,parser):
        parser.add_argument("--limit",type=int,default=20)

    def handle(self,*args,**options):
        limit=options["limit"]
        if limit<1 or limit>500:
            raise CommandError("--limit must be between 1 and 500.")
        ids=list(ResumeDocument.objects.filter(processing_status=ResumeProcessingStatus.PENDING).order_by("created_at").values_list("id",flat=True)[:limit])
        counts={"completed":0,"manual_review":0,"failed":0}
        for document_id in ids:
            doc=process_resume_document(ResumeDocument.objects.get(pk=document_id))
            if doc.processing_status==ResumeProcessingStatus.COMPLETED:
                counts["completed"]+=1
            elif doc.processing_status==ResumeProcessingStatus.NEEDS_MANUAL_REVIEW:
                counts["manual_review"]+=1
            elif doc.processing_status==ResumeProcessingStatus.FAILED:
                counts["failed"]+=1
        self.stdout.write(self.style.SUCCESS(
            f"Processed {len(ids)} resumes: {counts['completed']} completed, "
            f"{counts['manual_review']} manual review, {counts['failed']} failed."
        ))
