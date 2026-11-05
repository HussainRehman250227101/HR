"""Configurable, versioned scoring rubrics and immutable evaluation snapshots."""

import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


DEFAULT_SCORING_WEIGHTS = {
    "required_skills": 40,
    "relevant_experience": 25,
    "role_related_projects": 20,
    "education_certifications": 10,
    "other_job_evidence": 5,
}

CRITERION_LABELS = {
    "required_skills": "Required skills",
    "relevant_experience": "Relevant experience",
    "role_related_projects": "Role-related projects",
    "education_certifications": "Education and certifications",
    "other_job_evidence": "Other explicitly job-related evidence",
}


def default_scoring_weights():
    return DEFAULT_SCORING_WEIGHTS.copy()


class ScoringRubric(models.Model):
    """Immutable rubric version. Each requisition has at most one active version."""

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    requisition = models.ForeignKey(
        "requisitions.Requisition",
        on_delete=models.CASCADE,
        related_name="scoring_rubrics",
    )
    name = models.CharField(max_length=120, default="Default job-related rubric")
    weights = models.JSONField(default=default_scoring_weights)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scoring_rubrics_updated",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("requisition__title", "-version")
        constraints = [
            models.UniqueConstraint(
                fields=("requisition", "version"),
                name="unique_requisition_rubric_version",
            ),
            models.UniqueConstraint(
                fields=("requisition",),
                condition=Q(is_active=True),
                name="one_active_rubric_per_requisition",
            ),
        ]

    def __str__(self):
        state = "active" if self.is_active else "archived"
        return f"{self.requisition.title} — rubric v{self.version} ({state})"


class EvaluationRecommendation(models.TextChoices):
    REVIEW_RECOMMENDED = "REVIEW_RECOMMENDED", "Recruiter review recommended"
    MANUAL_REVIEW_REQUIRED = "MANUAL_REVIEW_REQUIRED", "Manual review required"


class ConfidenceLevel(models.TextChoices):
    HIGH = "HIGH", "High evidence coverage"
    MEDIUM = "MEDIUM", "Medium evidence coverage"
    LOW = "LOW", "Low evidence coverage"


class ResumeEvaluation(models.Model):
    """Immutable AI assessment snapshot. Human overrides are stored separately."""

    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.PROTECT, related_name="resume_evaluations"
    )
    requisition = models.ForeignKey(
        "requisitions.Requisition", on_delete=models.PROTECT, related_name="resume_evaluations"
    )
    resume_document = models.ForeignKey(
        "candidates.ResumeDocument", on_delete=models.PROTECT, related_name="evaluations"
    )
    rubric = models.ForeignKey(
        ScoringRubric, on_delete=models.PROTECT, related_name="evaluations"
    )
    version = models.PositiveIntegerField()
    overall_score = models.PositiveSmallIntegerField(null=True, blank=True)
    assessed_weight = models.PositiveSmallIntegerField(default=0)
    criterion_scores = models.JSONField(default=dict)
    evidence = models.JSONField(default=dict)
    missing_or_unclear_items = models.JSONField(default=list)
    parsing_warnings = models.JSONField(default=list)
    confidence_level = models.CharField(
        max_length=10, choices=ConfidenceLevel.choices, default=ConfidenceLevel.LOW
    )
    recommendation_for_human_review = models.CharField(
        max_length=32,
        choices=EvaluationRecommendation.choices,
        default=EvaluationRecommendation.MANUAL_REVIEW_REQUIRED,
    )
    overall_assessment = models.TextField(blank=True)
    provider = models.CharField(max_length=40, default="azure_openai")
    model_version = models.CharField(max_length=120)
    prompt_version = models.CharField(max_length=40, default="resume-scoring-v1")
    input_sha256 = models.CharField(max_length=64)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="resume_evaluations_created",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-version")
        constraints = [
            models.UniqueConstraint(fields=("resume_document", "version"), name="unique_resume_evaluation_version"),
            models.CheckConstraint(
                condition=Q(overall_score__isnull=True) | Q(overall_score__gte=0, overall_score__lte=100),
                name="valid_resume_overall_score",
            ),
        ]
        indexes = [
            models.Index(fields=("candidate", "created_at")),
            models.Index(fields=("requisition", "overall_score")),
        ]

    def __str__(self):
        score = "not calculated" if self.overall_score is None else f"{self.overall_score}/100"
        return f"{self.candidate} — {score} (v{self.version})"
