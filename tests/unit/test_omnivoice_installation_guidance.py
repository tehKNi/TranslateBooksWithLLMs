"""Source-level tests for OmniVoice installation guidance."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OMNIVOICE_PROVIDER = PROJECT_ROOT / "src" / "tts" / "providers" / "omnivoice.py"


def test_omnivoice_provider_contains_docker_install_guidance():
    """OmniVoice install guidance should mention Docker rebuilds for containers."""
    source = OMNIVOICE_PROVIDER.read_text(encoding="utf-8")

    assert "Path('/.dockerenv').exists()" in source
    assert "INSTALL_OMNIVOICE=1 docker compose up -d --build" in source
    assert "OmniVoice must be baked into the Docker image" in source
