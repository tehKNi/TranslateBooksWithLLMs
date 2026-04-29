"""Unit tests for OmniVoice provider registration."""

import pytest

from src.tts import audio_processor
from src.tts import providers
from src.tts.providers import omnivoice as omnivoice_tts


def test_providers_factory_supports_omnivoice(monkeypatch):
    """The providers package factory should dispatch the OmniVoice provider."""
    sentinel = object()

    monkeypatch.setattr(
        providers,
        "create_omnivoice_provider",
        lambda **kwargs: sentinel,
        raising=False,
    )

    provider = providers.create_provider(
        "omnivoice",
        omnivoice_mode="voice_design",
        omnivoice_instruct="female, warm, british accent",
    )

    assert provider is sentinel


def test_audio_processor_factory_supports_omnivoice(monkeypatch):
    """The audio processor factory should dispatch the OmniVoice provider."""
    sentinel = object()

    monkeypatch.setattr(
        audio_processor,
        "create_omnivoice_provider",
        lambda **kwargs: sentinel,
        raising=False,
    )

    provider = audio_processor.create_tts_provider(
        "omnivoice",
        omnivoice_mode="voice_cloning",
        omnivoice_ref_audio_path="prompt.wav",
    )

    assert provider is sentinel


def test_omnivoice_install_status_reports_missing_dependencies(monkeypatch):
    """Install guidance should expose missing OmniVoice runtime packages."""
    monkeypatch.setattr(omnivoice_tts, "TORCH_AVAILABLE", False)
    monkeypatch.setattr(omnivoice_tts, "TORCHAUDIO_AVAILABLE", False)
    monkeypatch.setattr(omnivoice_tts, "SOUNDFILE_AVAILABLE", False)
    monkeypatch.setattr(omnivoice_tts, "OMNIVOICE_AVAILABLE", False)

    status = omnivoice_tts.get_omnivoice_install_status()

    assert status["available"] is False
    assert status["install_method"] == "pip"
    assert "omnivoice" in status["missing_dependencies"]
    assert "torch" in status["missing_dependencies"]
    assert "torchaudio" in status["missing_dependencies"]
    assert "soundfile" in status["missing_dependencies"]

def test_build_generate_kwargs_for_voice_design_mode():
    """Voice design mode should translate config into OmniVoice kwargs."""
    provider = omnivoice_tts.OmniVoiceProvider.__new__(omnivoice_tts.OmniVoiceProvider)
    provider.omnivoice_mode = "voice_design"
    provider.omnivoice_ref_audio_path = ""
    provider.omnivoice_ref_text = ""
    provider.omnivoice_instruct = "female, warm, british accent"
    provider.omnivoice_speed = 1.1
    provider.omnivoice_duration = 7.5
    provider.omnivoice_num_step = 24

    kwargs = provider._build_generate_kwargs("Hello from OmniVoice")

    assert kwargs == {
        "text": "Hello from OmniVoice",
        "num_step": 24,
        "speed": 1.1,
        "duration": 7.5,
        "instruct": "female, warm, british accent",
    }


def test_build_generate_kwargs_for_voice_cloning_requires_reference_audio():
    """Voice cloning mode should fail fast when no prompt audio is configured."""
    provider = omnivoice_tts.OmniVoiceProvider.__new__(omnivoice_tts.OmniVoiceProvider)
    provider.omnivoice_mode = "voice_cloning"
    provider.omnivoice_ref_audio_path = ""
    provider.omnivoice_ref_text = ""
    provider.omnivoice_instruct = ""
    provider.omnivoice_speed = 1.0
    provider.omnivoice_duration = None
    provider.omnivoice_num_step = 32

    with pytest.raises(omnivoice_tts.TTSError, match="reference audio path"):
        provider._build_generate_kwargs("Clone this voice")
