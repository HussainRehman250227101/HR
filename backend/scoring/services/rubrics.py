"""Get the active requisition rubric, creating the SRS default on first use."""

from django.db import transaction

from scoring.models import DEFAULT_SCORING_WEIGHTS, ScoringRubric


def get_or_create_rubric(requisition):
    rubric = ScoringRubric.objects.filter(
        requisition=requisition, is_active=True
    ).order_by("-version").first()
    if rubric:
        return rubric
    with transaction.atomic():
        rubric = ScoringRubric.objects.filter(
            requisition=requisition, is_active=True
        ).order_by("-version").first()
        if rubric:
            return rubric
        return ScoringRubric.objects.create(
            requisition=requisition,
            name="Default job-related rubric",
            weights=DEFAULT_SCORING_WEIGHTS.copy(),
            version=1,
            is_active=True,
        )
