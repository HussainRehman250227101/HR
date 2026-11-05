"""Endpoints to start, inspect and safely resume candidate scoring workflows."""

from django.shortcuts import get_object_or_404
from rest_framework import exceptions, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsRecruiterOrAdmin
from candidates.models import Candidate, CandidateStatus, ResumeProcessingStatus
from .models import WorkflowRun, WorkflowRunStatus
from .serializers import WorkflowRunSerializer
from .services import retry_workflow_resume, start_scoring_workflow


class CandidateScoringWorkflowStartView(APIView):
    permission_classes = [IsRecruiterOrAdmin]

    def post(self, request, candidate_id):
        candidate = get_object_or_404(
            Candidate.objects.select_related("requisition"), public_id=candidate_id
        )
        if candidate.requisition.status != "OPEN":
            raise exceptions.ValidationError("Scoring workflows can only start for open requisitions.")
        if candidate.current_status not in {
            CandidateStatus.RESUME_RECEIVED,
            CandidateStatus.NEEDS_MANUAL_REVIEW,
            CandidateStatus.SCORED_HR_REVIEW,
        }:
            raise exceptions.ValidationError("This candidate is not at a status that permits resume scoring.")
        active = candidate.workflow_runs.filter(
            status__in=(
                WorkflowRunStatus.PENDING,
                WorkflowRunStatus.RUNNING,
                WorkflowRunStatus.WAITING_HR_REVIEW,
            )
        ).first()
        if active:
            raise exceptions.ValidationError({
                "workflow": f"A workflow is already active: {active.public_id} ({active.status})."
            })
        resume = candidate.resume_documents.filter(
            processing_status=ResumeProcessingStatus.COMPLETED
        ).order_by("-processed_at", "-created_at").first()
        if not resume:
            raise exceptions.ValidationError({
                "resume": "The candidate does not have a successfully processed resume."
            })
        run = WorkflowRun.objects.create(
            candidate=candidate,
            resume_document=resume,
            status=WorkflowRunStatus.PENDING,
            created_by=request.user,
        )
        run = start_scoring_workflow(run)
        response_status = (
            status.HTTP_202_ACCEPTED
            if run.status == WorkflowRunStatus.WAITING_HR_REVIEW
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        return Response(WorkflowRunSerializer(run).data, status=response_status)


class WorkflowRunDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, public_id):
        run = get_object_or_404(
            WorkflowRun.objects.select_related("candidate", "candidate__requisition", "resume_document", "evaluation"),
            public_id=public_id,
        )
        user = request.user
        allowed = (
            user.is_superuser
            or getattr(user, "role", None) in ("ADMIN", "RECRUITER")
            or (
                getattr(user, "role", None) == "HIRING_MANAGER"
                and run.candidate.requisition.hiring_manager_id == user.pk
            )
        )
        if not allowed:
            raise exceptions.PermissionDenied("You cannot access this workflow.")
        return Response(WorkflowRunSerializer(run).data)


class WorkflowRunResumeView(APIView):
    permission_classes = [IsRecruiterOrAdmin]

    def post(self, request, public_id):
        run = get_object_or_404(
            WorkflowRun.objects.select_related("candidate", "resume_document", "evaluation"),
            public_id=public_id,
        )
        try:
            run = retry_workflow_resume(run)
        except ValueError as exc:
            raise exceptions.ValidationError({"workflow": str(exc)}) from exc
        except Exception as exc:
            raise exceptions.APIException(
                "The workflow could not be resumed. The saved recruiter decision is preserved; retry later."
            ) from exc
        return Response(WorkflowRunSerializer(run).data)
