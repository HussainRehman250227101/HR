"""Recruiter-controlled shortlist review and candidate progression."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, permissions, status
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response

from accounts.permissions import IsRecruiterOrAdmin
from candidates.models import Candidate, CandidateEvent, CandidateStatus
from scoring.models import ResumeEvaluation
from scoring.serializers import EvaluationListSerializer
from workflows.models import WorkflowRun, WorkflowRunStatus
from workflows.services import resume_workflow_after_review
from .models import ShortlistDecision, ShortlistReview
from .serializers import ShortlistDecisionRequestSerializer, ShortlistReviewSerializer


REVIEWABLE_STATUSES = {CandidateStatus.SCORED_HR_REVIEW, CandidateStatus.NEEDS_MANUAL_REVIEW}


class ShortlistQueueView(GenericAPIView):
    permission_classes = [IsRecruiterOrAdmin]

    def get(self, request):
        queryset = Candidate.objects.filter(
            current_status__in=REVIEWABLE_STATUSES
        ).select_related("requisition")
        requisition_ref = request.query_params.get("requisition")
        if requisition_ref:
            queryset = queryset.filter(requisition__reference_code=requisition_ref)
        results = []
        for candidate in queryset.order_by("-updated_at"):
            evaluation = candidate.resume_evaluations.select_related("rubric").order_by("-created_at", "-version").first()
            if evaluation:
                results.append({
                    "candidate": {
                        "public_id": str(candidate.public_id),
                        "full_name": candidate.full_name,
                        "email": candidate.email,
                        "phone": candidate.phone,
                        "current_status": candidate.current_status,
                        "identity_review_required": candidate.identity_review_required,
                        "requisition_reference": str(candidate.requisition.reference_code),
                        "requisition_title": candidate.requisition.title,
                    },
                    "evaluation": EvaluationListSerializer(evaluation).data,
                })
        return Response({"count": len(results), "results": results})


class CandidateShortlistDecisionView(GenericAPIView):
    permission_classes = [IsRecruiterOrAdmin]
    serializer_class = ShortlistDecisionRequestSerializer

    def post(self, request, candidate_id):
        candidate = get_object_or_404(
            Candidate.objects.select_related("requisition"), public_id=candidate_id
        )
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        evaluation = get_object_or_404(ResumeEvaluation, public_id=data["evaluation"])

        if evaluation.candidate_id != candidate.pk:
            raise exceptions.ValidationError({"evaluation": "The selected evaluation does not belong to this candidate."})
        latest = candidate.resume_evaluations.order_by("-created_at", "-version").first()
        if latest is None or latest.pk != evaluation.pk:
            raise exceptions.ValidationError({"evaluation": "A shortlist decision must reference the candidate's latest evaluation."})
        if candidate.current_status not in REVIEWABLE_STATUSES:
            raise exceptions.ValidationError({"candidate_status": "This candidate is not awaiting recruiter shortlist review."})

        if data["decision"] == ShortlistDecision.APPROVE_FOR_SCREENING:
            # If the AI could not calculate a score, approval requires a reasoned human score override.
            if evaluation.overall_score is None and data.get("score_override") is None:
                raise exceptions.ValidationError({
                    "decision": "This evaluation has no defensible overall score. Provide a reasoned human score override or keep the candidate for manual review."
                })
            if candidate.identity_review_required:
                if not data.get("identity_verified"):
                    raise exceptions.ValidationError({"identity_verified": "Confirm candidate identity review before approving screening."})
                if not candidate.full_name.strip() or not (candidate.email or candidate.phone):
                    raise exceptions.ValidationError({"candidate_details": "Enter the candidate name and at least one contact method before confirming identity."})

        previous_status = candidate.current_status
        if data["decision"] == ShortlistDecision.APPROVE_FOR_SCREENING:
            resulting_status = CandidateStatus.APPROVED_FOR_SCREENING
        elif data["decision"] == ShortlistDecision.DECLINE:
            resulting_status = CandidateStatus.CLOSED
        else:
            resulting_status = CandidateStatus.NEEDS_MANUAL_REVIEW

        with transaction.atomic():
            review = ShortlistReview.objects.create(
                candidate=candidate,
                evaluation=evaluation,
                decision=data["decision"],
                decision_reason=data["decision_reason"],
                score_override=data.get("score_override"),
                score_override_reason=data.get("score_override_reason", ""),
                previous_candidate_status=previous_status,
                resulting_candidate_status=resulting_status,
                decided_by=request.user,
            )
            identity_was_pending = candidate.identity_review_required
            candidate.current_status = resulting_status
            if data.get("identity_verified"):
                candidate.identity_review_required = False
            if resulting_status == CandidateStatus.CLOSED:
                candidate.closed_reason = data["decision_reason"]
                candidate.save(update_fields=("current_status", "closed_reason", "identity_review_required", "updated_at"))
            else:
                candidate.save(update_fields=("current_status", "identity_review_required", "updated_at"))
            if identity_was_pending and data.get("identity_verified"):
                CandidateEvent.objects.create(
                    candidate=candidate, actor=request.user,
                    event_type=CandidateEvent.EventType.CANDIDATE_IDENTITY_REVIEWED,
                    details={"review_reason": data.get("identity_review_reason", "")},
                )
            CandidateEvent.objects.create(
                candidate=candidate, actor=request.user,
                event_type=CandidateEvent.EventType.SHORTLIST_DECISION_RECORDED,
                details={
                    "shortlist_review_id": str(review.public_id),
                    "evaluation_id": str(evaluation.public_id),
                    "decision": review.decision,
                    "from": previous_status,
                    "to": resulting_status,
                    "score_override": review.score_override,
                },
            )

        run = WorkflowRun.objects.filter(
            evaluation=evaluation,
            status=WorkflowRunStatus.WAITING_HR_REVIEW,
        ).order_by("-created_at").first()
        if run:
            try:
                resume_workflow_after_review(run, review)
            except Exception:
                # The decision is durable; POST /api/v1/workflows/<run_uuid>/resume/ retries safely.
                run.refresh_from_db()

        return Response({
            "review": ShortlistReviewSerializer(review).data,
            "candidate_status": resulting_status,
            "workflow_run": str(run.public_id) if run else None,
            "workflow_status": run.status if run else None,
        }, status=status.HTTP_201_CREATED)


class CandidateShortlistHistoryView(GenericAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, candidate_id):
        candidate = get_object_or_404(Candidate, public_id=candidate_id)
        user = request.user
        allowed = (
            user.is_superuser
            or getattr(user, "role", None) in ("ADMIN", "RECRUITER")
            or (
                getattr(user, "role", None) == "HIRING_MANAGER"
                and candidate.requisition.hiring_manager_id == user.pk
            )
        )
        if not allowed:
            raise exceptions.PermissionDenied("You cannot access this review history.")
        reviews = candidate.shortlist_reviews.select_related("evaluation", "decided_by").all()
        return Response(ShortlistReviewSerializer(reviews, many=True).data)
