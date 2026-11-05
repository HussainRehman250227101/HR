"""Append-only human shortlist decisions and score overrides."""

import uuid

from django.conf import settings
from django.db import models


class ShortlistDecision(models.TextChoices):
    APPROVE_FOR_SCREENING = "APPROVE_FOR_SCREENING", "Approve for Screening"
    DECLINE = "DECLINE", "Decline"
    HOLD_FOR_REVIEW = "HOLD_FOR_REVIEW", "Hold for Manual Review"


class ShortlistReview(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    candidate = models.ForeignKey(
        "candidates.Candidate", on_delete=models.PROTECT, related_name="shortlist_reviews"
    )
    evaluation = models.ForeignKey(
        "scoring.ResumeEvaluation", on_delete=models.PROTECT, related_name="shortlist_reviews"
    )
    decision = models.CharField(max_length=24, choices=ShortlistDecision.choices)
    decision_reason = models.TextField()
    score_override = models.PositiveSmallIntegerField(null=True, blank=True)
    score_override_reason = models.TextField(blank=True)
    previous_candidate_status = models.CharField(max_length=40)
    resulting_candidate_status = models.CharField(max_length=40)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="shortlist_reviews_decided"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("candidate", "created_at")),
            models.Index(fields=("decision", "created_at")),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score_override__isnull=True) | models.Q(score_override__gte=0, score_override__lte=100),
                name="valid_shortlist_score_override",
            ),
        ]

    def __str__(self):
        return f"{self.candidate} — {self.get_decision_display()}"
