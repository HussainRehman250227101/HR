from django.urls import path

from .views import LLMStatusView,LLMTestConnectionView

app_name="llm"
urlpatterns=[
    path("status/",LLMStatusView.as_view(),name="status"),
    path("test/",LLMTestConnectionView.as_view(),name="test-connection"),
]
