from django.urls import path

from .views import (
    CandidateShortlistDecisionView,
    CandidateShortlistHistoryView,
    ShortlistQueueView,
)

app_name = "reviews"
urlpatterns = [
    path("shortlist/", ShortlistQueueView.as_view(), name="shortlist-queue"),
    path("candidates/<uuid:candidate_id>/shortlist/", CandidateShortlistDecisionView.as_view(), name="candidate-shortlist-decision"),
    path("candidates/<uuid:candidate_id>/history/", CandidateShortlistHistoryView.as_view(), name="candidate-shortlist-history"),
]
