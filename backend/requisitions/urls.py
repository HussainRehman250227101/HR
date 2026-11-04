from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import RequisitionViewSet

app_name = "requisitions"

router = DefaultRouter()
router.register(r"", RequisitionViewSet, basename="requisition")

urlpatterns = [
    path("", include(router.urls)),
]
