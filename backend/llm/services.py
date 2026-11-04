"""Shared Azure OpenAI v1 client for text and schema-constrained output."""

import logging
from functools import cached_property
from urllib.parse import urlsplit

from django.conf import settings
from openai import OpenAI,OpenAIError
from pydantic import BaseModel

from .exceptions import LLMConfigurationError,LLMProviderError,LLMStructuredOutputError

logger=logging.getLogger(__name__)


class AzureOpenAIProvider:
    """Use the exact Azure deployment name as the SDK model argument."""

    @property
    def is_configured(self):
        return all((
            getattr(settings,"AZURE_OPENAI_ENDPOINT",""),
            getattr(settings,"AZURE_OPENAI_API_KEY",""),
            getattr(settings,"AZURE_OPENAI_CHAT_DEPLOYMENT",""),
        ))

    @property
    def deployment_name(self):
        return getattr(settings,"AZURE_OPENAI_CHAT_DEPLOYMENT","")

    @property
    def base_url(self):
        endpoint=getattr(settings,"AZURE_OPENAI_ENDPOINT","").strip()
        parsed=urlsplit(endpoint)
        if parsed.scheme!="https" or not parsed.netloc:
            raise LLMConfigurationError("AZURE_OPENAI_ENDPOINT must be a valid HTTPS endpoint.")
        base=endpoint.rstrip("/")
        if not base.endswith("/openai/v1"):
            base=f"{base}/openai/v1"
        return f"{base}/"

    @cached_property
    def client(self):
        api_key=getattr(settings,"AZURE_OPENAI_API_KEY","").strip()
        if not api_key:
            raise LLMConfigurationError("AZURE_OPENAI_API_KEY is not configured.")
        if not self.deployment_name:
            raise LLMConfigurationError("AZURE_OPENAI_CHAT_DEPLOYMENT is not configured.")
        return OpenAI(
            api_key=api_key,
            base_url=self.base_url,
            timeout=settings.AZURE_OPENAI_TIMEOUT_SECONDS,
            max_retries=settings.AZURE_OPENAI_MAX_RETRIES,
        )

    def generate_text(self,messages:list[dict[str,str]],max_completion_tokens:int|None=None)->str:
        if not messages:
            raise ValueError("At least one chat message is required.")
        limit=max_completion_tokens or settings.AZURE_OPENAI_MAX_COMPLETION_TOKENS
        try:
            completion=self.client.chat.completions.create(
                model=self.deployment_name,
                messages=messages,
                max_completion_tokens=limit,
                reasoning_effort=settings.AZURE_OPENAI_REASONING_EFFORT,
            )
            message=completion.choices[0].message
        except OpenAIError as exc:
            logger.warning("Azure OpenAI request failed. deployment=%s exception_type=%s",self.deployment_name,type(exc).__name__)
            raise LLMProviderError("Azure OpenAI request failed. Verify deployment, endpoint, credentials and service availability.") from exc
        if getattr(message,"refusal",None):
            raise LLMProviderError("The model declined the request.")
        content=message.content
        if not content or not content.strip():
            raise LLMProviderError("The model returned an empty response.")
        logger.info("Azure OpenAI request completed. deployment=%s",self.deployment_name)
        return content.strip()

    def generate_structured(self,messages:list[dict[str,str]],response_model:type[BaseModel],max_completion_tokens:int|None=None)->BaseModel:
        if not messages:
            raise ValueError("At least one chat message is required.")
        limit=max_completion_tokens or settings.AZURE_OPENAI_MAX_COMPLETION_TOKENS
        try:
            completion=self.client.chat.completions.parse(
                model=self.deployment_name,
                messages=messages,
                response_format=response_model,
                max_completion_tokens=limit,
                reasoning_effort=settings.AZURE_OPENAI_REASONING_EFFORT,
            )
            message=completion.choices[0].message
        except OpenAIError as exc:
            logger.warning("Azure OpenAI structured request failed. deployment=%s exception_type=%s",self.deployment_name,type(exc).__name__)
            raise LLMProviderError("Azure OpenAI structured request failed. Verify deployment support and service availability.") from exc
        if getattr(message,"refusal",None):
            raise LLMStructuredOutputError("The model declined the structured-output request.")
        if message.parsed is None:
            raise LLMStructuredOutputError("The model did not return output matching the required schema.")
        logger.info("Azure OpenAI structured request completed. deployment=%s schema=%s",self.deployment_name,response_model.__name__)
        return message.parsed


def get_llm_provider():
    return AzureOpenAIProvider()
