"""Unit tests for llama.cpp web provider exposure."""

from pathlib import Path


def test_translation_interface_contains_llama_cpp_provider():
    """The main translation interface should expose llama.cpp as a provider option."""
    html = Path("src/web/templates/translation_interface.html").read_text(encoding="utf-8")

    assert 'value="llama_cpp"' in html
    assert "llama.cpp" in html


def test_provider_manager_contains_llama_cpp_metadata():
    """The web provider manager should know how to display llama.cpp."""
    source = Path("src/web/static/js/providers/provider-manager.js").read_text(encoding="utf-8")

    assert "llama_cpp" in source
    assert "llama.cpp" in source
