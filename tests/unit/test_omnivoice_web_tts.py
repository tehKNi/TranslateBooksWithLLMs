"""Tests for OmniVoice controls in the web TTS surface."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = PROJECT_ROOT / "src" / "web" / "templates" / "translation_interface.html"


def test_translation_interface_contains_omnivoice_controls():
    """The main translation template should expose OmniVoice TTS controls."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    required_ids = [
        'ttsEnabled',
        'ttsOptions',
        'ttsProvider',
        'omnivoiceOptions',
        'omnivoiceMode',
        'omnivoiceInstruct',
        'omnivoiceRefAudioPath',
        'omnivoiceRefText',
        'omnivoiceSpeed',
        'omnivoiceDuration',
        'omnivoiceNumStep',
    ]

    for element_id in required_ids:
        assert f'id="{element_id}"' in template


@pytest.mark.skipif(shutil.which("node") is None, reason="Node.js is required for JS payload tests")
def test_tts_request_config_includes_omnivoice_fields():
    """The JS request builder should include OmniVoice-specific fields."""
    script = """
import { buildTTSRequestConfig } from './src/web/static/js/tts/tts-request-config.js';

const result = buildTTSRequestConfig({
  ttsEnabled: true,
  ttsProvider: 'omnivoice',
  ttsVoice: '',
  ttsFormat: 'wav',
  ttsBitrate: '96k',
  omnivoiceMode: 'voice_design',
  omnivoiceInstruct: 'female, low pitch',
  omnivoiceRefAudioPath: '',
  omnivoiceRefText: '',
  omnivoiceSpeed: '1.2',
  omnivoiceDuration: '8.5',
  omnivoiceNumStep: '24'
});

console.log(JSON.stringify(result));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = json.loads(result.stdout.strip())

    assert payload["tts_provider"] == "omnivoice"
    assert payload["tts_omnivoice_mode"] == "voice_design"
    assert payload["tts_omnivoice_instruct"] == "female, low pitch"
    assert payload["tts_omnivoice_speed"] == 1.2
    assert payload["tts_omnivoice_duration"] == 8.5
    assert payload["tts_omnivoice_num_step"] == 24
