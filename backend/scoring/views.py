"""Scoring endpoints for recruiter-run evaluations and immutable rubric versions."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import exceptions, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsRecruiterOrAdmin
from candidates.models import Candidate
from llm.exceptions import LLMConfigurationError, LLMProviderError
from requisitions.models import Requisition
from .models import ResumeEvaluation, ScoringRubric
from .serializers import EvaluationDetailSerializer, EvaluationListSerializer, EvaluationRequestSerializer, ScoringRubricSerializer
from .services.agent import evaluate_candidate_resume
from .services.rubrics import get_or_create_rubric


class RequisitionRubricView(APIView):
    permission_classes = [IsRecruiterOrAdmin]

    def get(self, request, reference_code):
        requisition = get_object_or_404(Requisition, reference_code=reference_code)
        rubric = get_or_create_rubric(requisition)
        return Response(ScoringRubricSerializer(rubric).data)

    def put(self, request, reference_code):
        requisition = get_object_or_404(Requisition, reference_code=reference_code)
        current = get_or_create_rubric(requisition)
        serializer = ScoringRubricSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            current.is_active = False
            current.save(update_fields=("is_active", "updated_at"))
            rubric = ScoringRubric.objects.create(
                requisition=requisition,
                name=data.get("name", current.name),
                weights=data["weights"],
                version=current.version + 1,
                is_active=True,
                notes=data.get("notes", ""),
                updated_by=request.user,
            )
        return Response(ScoringRubricSerializer(rubric).data)


class CandidateEvaluationView(APIView):
    permission_classes = [IsRecruiterOrAdmin]

    def post(self, request, candidate_id):
        candidate = get_object_or_404(Candidate, public_id=candidate_id)
        serializer = EvaluationRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            evaluation = evaluate_candidate_resume(
                candidate_id=candidate.pk,
                resume_document_id=serializer.validated_data.get("resume_document"),
                actor=request.user,
            )
        except ValueError as exc:
            raise exceptions.ValidationError({"detail": str(exc)}) from exc
        except (LLMConfigurationError, LLMProviderError) as exc:
            raise exceptions.APIException("The scoring provider could not complete this evaluation. Check Azure configuration and retry later.") from exc
        return Response(EvaluationDetailSerializer(evaluation).data, status=status.HTTP_201_CREATED)


class CandidateEvaluationHistoryView(APIView):
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
            raise exceptions.PermissionDenied("You cannot access this candidate's evaluations.")
        evaluations = candidate.resume_evaluations.select_related("rubric").all()
        return Response(EvaluationListSerializer(evaluations, many=True).data)


class EvaluationDetailView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, public_id):
        evaluation = get_object_or_404(
            ResumeEvaluation.objects.select_related("candidate", "requisition", "resume_document", "rubric"),
            public_id=public_id,
        )
        user = request.user
        allowed = (
            user.is_superuser
            or getattr(user, "role", None) in ("ADMIN", "RECRUITER")
            or (
                getattr(user, "role", None) == "HIRING_MANAGER"
                and evaluation.requisition.hiring_manager_id == user.pk
            )
        )
        if not allowed:
            raise exceptions.PermissionDenied("You cannot access this evaluation.")
        return Response(EvaluationDetailSerializer(evaluation).data)
