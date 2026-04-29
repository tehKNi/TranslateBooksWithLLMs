"""Unit tests for OmniVoice TTS configuration parsing."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace


def load_tts_config_module():
    """Import tts_config directly to avoid package-level side effects."""
    project_root = Path(__file__).resolve().parents[2]
    module_path = project_root / "src" / "tts" / "tts_config.py"
    spec = spec_from_file_location("test_tts_config_module", module_path)
    module = module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_from_cli_args_reads_omnivoice_fields():
    """CLI parsing should keep OmniVoice-specific options intact."""
    tts_config_module = load_tts_config_module()

    args = SimpleNamespace(
        tts=True,
        tts_provider="omnivoice",
        tts_voice="",
        tts_rate="+5%",
        tts_bitrate="96k",
        tts_format="wav",
        omnivoice_mode="voice_design",
        omnivoice_ref_audio="sample.wav",
        omnivoice_ref_text="Reference speech",
        omnivoice_instruct="female, low pitch, british accent",
        omnivoice_speed=1.15,
        omnivoice_duration=8.5,
        omnivoice_num_step=24,
    )

    config = tts_config_module.TTSConfig.from_cli_args(args)

    assert config.enabled is True
    assert config.provider == "omnivoice"
    assert config.rate == "+5%"
    assert config.output_format == "wav"
    assert config.omnivoice_mode == "voice_design"
    assert config.omnivoice_ref_audio_path == "sample.wav"
    assert config.omnivoice_ref_text == "Reference speech"
    assert config.omnivoice_instruct == "female, low pitch, british accent"
    assert config.omnivoice_speed == 1.15
    assert config.omnivoice_duration == 8.5
    assert config.omnivoice_num_step == 24


def test_from_web_request_serializes_omnivoice_fields():
    """Web request parsing should expose OmniVoice values through to_dict()."""
    tts_config_module = load_tts_config_module()

    request_data = {
        "tts_enabled": True,
        "tts_provider": "omnivoice",
        "tts_rate": "+0%",
        "tts_format": "wav",
        "tts_omnivoice_mode": "voice_cloning",
        "tts_omnivoice_ref_audio_path": "uploads\\prompt.wav",
        "tts_omnivoice_ref_text": "Prompt transcript",
        "tts_omnivoice_instruct": "male, cheerful",
        "tts_omnivoice_speed": "1.05",
        "tts_omnivoice_duration": "6.25",
        "tts_omnivoice_num_step": "16",
    }

    config = tts_config_module.TTSConfig.from_web_request(request_data)
    payload = config.to_dict()

    assert config.provider == "omnivoice"
    assert config.omnivoice_mode == "voice_cloning"
    assert config.omnivoice_ref_audio_path == "uploads\\prompt.wav"
    assert config.omnivoice_ref_text == "Prompt transcript"
    assert config.omnivoice_instruct == "male, cheerful"
    assert config.omnivoice_speed == 1.05
    assert config.omnivoice_duration == 6.25
    assert config.omnivoice_num_step == 16

    assert payload["omnivoice_mode"] == "voice_cloning"
    assert payload["omnivoice_ref_audio_path"] == "uploads\\prompt.wav"
    assert payload["omnivoice_ref_text"] == "Prompt transcript"
    assert payload["omnivoice_instruct"] == "male, cheerful"
    assert payload["omnivoice_speed"] == 1.05
    assert payload["omnivoice_duration"] == 6.25
    assert payload["omnivoice_num_step"] == 16
