"""Admin-only LLM status and opt-in connectivity checks."""

from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsHRAdmin
from .exceptions import LLMConfigurationError,LLMProviderError
from .schemas import LLMProbeResult
from .serializers import LLMTestRequestSerializer
from .services import get_llm_provider


class LLMStatusView(APIView):
    permission_classes=[IsHRAdmin]

    def get(self,request):
        provider=get_llm_provider()
        return Response({
            "provider":"azure_openai",
            "configured":provider.is_configured,
            "deployment":provider.deployment_name or None,
            "api_style":"Azure OpenAI v1",
            "structured_outputs":True,
            "timeout_seconds":settings.AZURE_OPENAI_TIMEOUT_SECONDS,
            "max_retries":settings.AZURE_OPENAI_MAX_RETRIES,
        })


class LLMTestConnectionView(APIView):
    permission_classes=[IsHRAdmin]

    def post(self,request):
        serializer=LLMTestRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        provider=get_llm_provider()
        if not provider.is_configured:
            return Response(
                {"success":False,"detail":"Azure OpenAI is not fully configured. Check endpoint, key and deployment in backend/.env."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        try:
            result=provider.generate_structured(
                messages=[
                    {"role":"system","content":"Connectivity check. Return status READY and a short confirmation message."},
                    {"role":"user","content":serializer.validated_data["prompt"]},
                ],
                response_model=LLMProbeResult,
                max_completion_tokens=100,
            )
        except (LLMConfigurationError,LLMProviderError) as exc:
            return Response({"success":False,"detail":str(exc)},status=status.HTTP_502_BAD_GATEWAY)
        return Response({"success":True,"deployment":provider.deployment_name,"result":result.model_dump()})
