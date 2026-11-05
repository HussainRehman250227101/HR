from types import SimpleNamespace
from unittest.mock import Mock,patch

from django.test import SimpleTestCase,override_settings
from rest_framework.test import APIRequestFactory,force_authenticate

from accounts.models import UserRole
from .exceptions import LLMConfigurationError
from .schemas import LLMProbeResult
from .services import AzureOpenAIProvider
from .views import LLMStatusView,LLMTestConnectionView


class AzureOpenAIProviderTests(SimpleTestCase):
    @override_settings(AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com",AZURE_OPENAI_API_KEY="test-key",AZURE_OPENAI_CHAT_DEPLOYMENT="hr-gpt-5-mini")
    def test_base_url_normalization(self):
        provider=AzureOpenAIProvider()
        self.assertEqual(provider.base_url,"https://example.openai.azure.com/openai/v1/")
        self.assertTrue(provider.is_configured)

    @override_settings(AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com/openai/v1/",AZURE_OPENAI_API_KEY="test-key",AZURE_OPENAI_CHAT_DEPLOYMENT="hr-gpt-5-mini")
    def test_existing_v1_path_is_not_duplicated(self):
        self.assertEqual(AzureOpenAIProvider().base_url,"https://example.openai.azure.com/openai/v1/")

    @override_settings(AZURE_OPENAI_ENDPOINT="",AZURE_OPENAI_API_KEY="",AZURE_OPENAI_CHAT_DEPLOYMENT="")
    def test_missing_configuration_fails_without_network(self):
        provider=AzureOpenAIProvider()
        self.assertFalse(provider.is_configured)
        with self.assertRaises(LLMConfigurationError):
            _=provider.client

    @override_settings(AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com",AZURE_OPENAI_API_KEY="test-key",AZURE_OPENAI_CHAT_DEPLOYMENT="hr-gpt-5-mini",AZURE_OPENAI_TIMEOUT_SECONDS=30,AZURE_OPENAI_MAX_RETRIES=2,AZURE_OPENAI_MAX_COMPLETION_TOKENS=500,AZURE_OPENAI_REASONING_EFFORT="low")
    @patch("llm.services.OpenAI")
    def test_text_generation_uses_azure_deployment(self,openai_cls):
        msg=SimpleNamespace(content="READY",refusal=None)
        create=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=msg)]))
        openai_cls.return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
        result=AzureOpenAIProvider().generate_text([{"role":"user","content":"Say READY"}])
        self.assertEqual(result,"READY")
        self.assertEqual(create.call_args.kwargs["model"],"hr-gpt-5-mini")
        self.assertEqual(create.call_args.kwargs["max_completion_tokens"],500)
        self.assertNotIn("temperature",create.call_args.kwargs)

    @override_settings(AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com",AZURE_OPENAI_API_KEY="test-key",AZURE_OPENAI_CHAT_DEPLOYMENT="hr-gpt-5-mini",AZURE_OPENAI_TIMEOUT_SECONDS=30,AZURE_OPENAI_MAX_RETRIES=2,AZURE_OPENAI_MAX_COMPLETION_TOKENS=500,AZURE_OPENAI_REASONING_EFFORT="low")
    @patch("llm.services.OpenAI")
    def test_structured_generation_returns_parsed_pydantic_object(self,openai_cls):
        parsed=LLMProbeResult(status="READY",message="Connected")
        msg=SimpleNamespace(parsed=parsed,refusal=None)
        parse=Mock(return_value=SimpleNamespace(choices=[SimpleNamespace(message=msg)]))
        openai_cls.return_value=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(parse=parse)))
        result=AzureOpenAIProvider().generate_structured([{"role":"user","content":"Return READY"}],LLMProbeResult)
        self.assertEqual(result.status,"READY")


class LLMEndpointTests(SimpleTestCase):
    def setUp(self):
        self.factory=APIRequestFactory()
        self.admin=SimpleNamespace(pk=1,is_authenticated=True,is_superuser=False,role=UserRole.ADMIN)

    @override_settings(AZURE_OPENAI_ENDPOINT="",AZURE_OPENAI_API_KEY="",AZURE_OPENAI_CHAT_DEPLOYMENT="",AZURE_OPENAI_TIMEOUT_SECONDS=30,AZURE_OPENAI_MAX_RETRIES=2)
    def test_status_does_not_expose_secret(self):
        request=self.factory.get("/api/v1/ai/status/")
        force_authenticate(request,user=self.admin)
        response=LLMStatusView.as_view()(request)
        self.assertEqual(response.status_code,200)
        self.assertFalse(response.data["configured"])
        self.assertNotIn("api_key",response.data)

    @override_settings(AZURE_OPENAI_ENDPOINT="",AZURE_OPENAI_API_KEY="",AZURE_OPENAI_CHAT_DEPLOYMENT="")
    def test_live_test_endpoint_returns_503_when_unconfigured(self):
        request=self.factory.post("/api/v1/ai/test/",{},format="json")
        force_authenticate(request,user=self.admin)
        response=LLMTestConnectionView.as_view()(request)
        self.assertEqual(response.status_code,503)
