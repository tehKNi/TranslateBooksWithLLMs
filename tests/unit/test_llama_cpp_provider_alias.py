"""Unit tests for llama.cpp provider alias support."""

from src.core.llm.factory import create_llm_provider
from src.core.llm.providers.openai import OpenAICompatibleProvider


def test_create_llm_provider_supports_llama_cpp_alias():
    """The factory should expose llama.cpp as a first-class provider alias."""
    provider = create_llm_provider(
        "llama_cpp",
        api_endpoint="http://localhost:8080/v1/chat/completions",
        model="qwen2.5-7b-instruct",
    )

    assert isinstance(provider, OpenAICompatibleProvider)
    assert provider.api_endpoint == "http://localhost:8080/v1/chat/completions"
    assert provider.model == "qwen2.5-7b-instruct"
