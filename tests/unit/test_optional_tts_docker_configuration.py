"""Unit tests for optional Docker TTS build configuration."""

from pathlib import Path

import yaml


def _load_compose(path: str) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def test_dockerfile_exposes_optional_tts_build_args():
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")

    assert "ARG INSTALL_CHATTERBOX=0" in dockerfile
    assert "ARG INSTALL_OMNIVOICE=0" in dockerfile
    assert 'if [ "$INSTALL_CHATTERBOX" = "1" ]' in dockerfile
    assert 'if [ "$INSTALL_OMNIVOICE" = "1" ]' in dockerfile


def test_main_compose_passes_optional_tts_build_args():
    compose = _load_compose("docker-compose.yml")
    service = compose["services"]["translate-book"]

    assert service["build"]["context"] == "."
    assert service["build"]["args"]["INSTALL_CHATTERBOX"] == "${INSTALL_CHATTERBOX:-0}"
    assert service["build"]["args"]["INSTALL_OMNIVOICE"] == "${INSTALL_OMNIVOICE:-0}"


def test_remote_ollama_compose_passes_optional_tts_build_args():
    compose = _load_compose("docker-compose.remote-ollama.example.yml")
    service = compose["services"]["translate-book"]

    assert service["build"]["context"] == "."
    assert service["build"]["args"]["INSTALL_CHATTERBOX"] == "${INSTALL_CHATTERBOX:-0}"
    assert service["build"]["args"]["INSTALL_OMNIVOICE"] == "${INSTALL_OMNIVOICE:-0}"
