"""Unit tests for OmniVoice-specific audio processor behavior."""

import asyncio
from pathlib import Path

from src.tts.audio_processor import AudioProcessor
from src.tts.providers.base import TTSProvider, TTSResult
from src.tts.tts_config import TTSConfig


class RecordingOmniVoiceProvider(TTSProvider):
    """Simple provider stub that records intermediate file paths."""

    def __init__(self):
        self.output_paths = []

    @property
    def name(self) -> str:
        return "omnivoice"

    @property
    def supports_streaming(self) -> bool:
        return False

    async def synthesize(self, text, voice, rate="+0%", volume="+0%", pitch="+0Hz") -> bytes:
        return b"RIFFfake-wav-data"

    async def synthesize_to_file(self, text, output_path, voice, rate="+0%", volume="+0%", pitch="+0Hz"):
        self.output_paths.append(output_path)
        Path(output_path).write_bytes(b"RIFFfake-wav-data")
        return TTSResult(success=True, output_path=output_path)

    async def get_available_voices(self, language_filter=None):
        return []


def test_generate_audio_uses_wav_temp_files_for_omnivoice(tmp_path):
    """OmniVoice intermediates should use WAV temp files, not MP3 temp files."""
    provider = RecordingOmniVoiceProvider()
    config = TTSConfig(voice="ignored", output_format="wav")
    processor = AudioProcessor(config, provider)

    success, message = asyncio.run(
        processor.generate_audio(
            text="Short OmniVoice sentence.",
            output_path=str(tmp_path / "output.wav"),
            language="English",
        )
    )

    assert success is True, message
    assert provider.output_paths
    assert provider.output_paths[0].endswith(".wav")
