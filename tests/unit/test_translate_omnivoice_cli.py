"""Unit tests for OmniVoice CLI exposure."""

import importlib

import pytest


translate = importlib.import_module("translate")


def test_build_parser_parses_omnivoice_tts_arguments():
    """The CLI parser should expose OmniVoice TTS options."""
    parser = translate.build_parser()

    args = parser.parse_args([
        "-i", "book.txt",
        "--tts",
        "--tts-provider", "omnivoice",
        "--omnivoice-mode", "voice_design",
        "--omnivoice-instruct", "female, low pitch",
        "--omnivoice-speed", "1.2",
        "--omnivoice-duration", "8.5",
        "--omnivoice-num-step", "24",
    ])

    assert args.tts is True
    assert args.tts_provider == "omnivoice"
    assert args.omnivoice_mode == "voice_design"
    assert args.omnivoice_instruct == "female, low pitch"
    assert args.omnivoice_speed == 1.2
    assert args.omnivoice_duration == 8.5
    assert args.omnivoice_num_step == 24


def test_validate_cli_args_rejects_unavailable_omnivoice(monkeypatch):
    """Explicit OmniVoice selection should fail fast when the runtime is unavailable."""
    parser = translate.build_parser()
    args = parser.parse_args([
        "-i", "book.txt",
        "--tts",
        "--tts-provider", "omnivoice",
    ])

    monkeypatch.setattr(translate, "is_omnivoice_available", lambda: False, raising=False)
    monkeypatch.setattr(
        translate,
        "get_omnivoice_install_status",
        lambda: {"missing_dependencies": ["omnivoice", "torch"]},
        raising=False,
    )

    with pytest.raises(SystemExit):
        translate.validate_cli_args(parser, args)
