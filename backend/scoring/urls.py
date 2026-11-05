from django.urls import path

from .views import (
    CandidateEvaluationHistoryView,
    CandidateEvaluationView,
    EvaluationDetailView,
    RequisitionRubricView,
)

app_name = "scoring"
urlpatterns = [
    path("requisitions/<uuid:reference_code>/rubric/", RequisitionRubricView.as_view(), name="requisition-rubric"),
    path("candidates/<uuid:candidate_id>/evaluate/", CandidateEvaluationView.as_view(), name="candidate-evaluate"),
    path("candidates/<uuid:candidate_id>/evaluations/", CandidateEvaluationHistoryView.as_view(), name="candidate-evaluation-history"),
    path("evaluations/<uuid:public_id>/", EvaluationDetailView.as_view(), name="evaluation-detail"),
]
