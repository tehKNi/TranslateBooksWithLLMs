"""
OmniVoice TTS provider implementation.

Wraps the official OmniVoice Python SDK behind the project's TTSProvider
interface while keeping the dependency optional and lazy-loaded.
"""

import asyncio
import io
import logging
from pathlib import Path
from typing import List, Optional

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    torch = None

try:
    import torchaudio
    TORCHAUDIO_AVAILABLE = True
except ImportError:
    TORCHAUDIO_AVAILABLE = False

try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError:
    SOUNDFILE_AVAILABLE = False
    sf = None

try:
    from omnivoice import OmniVoice
    OMNIVOICE_AVAILABLE = True
except ImportError:
    OMNIVOICE_AVAILABLE = False
    OmniVoice = None

from .base import TTSProvider, TTSResult, VoiceInfo, TTSError

logger = logging.getLogger(__name__)

DEFAULT_NUM_STEP = 32
DEFAULT_SAMPLE_RATE = 24000


class OmniVoiceProvider(TTSProvider):
    """TTS provider using the official OmniVoice Python SDK."""

    def __init__(
        self,
        omnivoice_mode: str = "auto",
        omnivoice_ref_audio_path: str = "",
        omnivoice_ref_text: str = "",
        omnivoice_instruct: str = "",
        omnivoice_speed: float = 1.0,
        omnivoice_duration: Optional[float] = None,
        omnivoice_num_step: int = DEFAULT_NUM_STEP,
    ):
        self._validate_dependencies()
        self.omnivoice_mode = omnivoice_mode
        self.omnivoice_ref_audio_path = omnivoice_ref_audio_path
        self.omnivoice_ref_text = omnivoice_ref_text
        self.omnivoice_instruct = omnivoice_instruct
        self.omnivoice_speed = omnivoice_speed
        self.omnivoice_duration = omnivoice_duration
        self.omnivoice_num_step = omnivoice_num_step

        self.device = self._resolve_device()
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        self._model = None
        self._model_loading = False

    @property
    def name(self) -> str:
        return "omnivoice"

    @property
    def supports_streaming(self) -> bool:
        return False

    def _validate_dependencies(self):
        missing = get_omnivoice_missing_dependencies()
        if missing:
            raise TTSError(
                f"Missing dependencies: {', '.join(missing)}. "
                f"Install with: pip install omnivoice torch torchaudio",
                provider="omnivoice",
                recoverable=False,
            )

    def _resolve_device(self) -> str:
        if not TORCH_AVAILABLE:
            return "cpu"
        if torch.cuda.is_available():
            return "cuda"
        return "cpu"

    async def _load_model(self):
        if self._model is not None:
            return
        if self._model_loading:
            while self._model_loading:
                await asyncio.sleep(0.1)
            return

        self._model_loading = True
        try:
            loop = asyncio.get_running_loop()
            self._model = await loop.run_in_executor(None, self._load_model_sync)
        except Exception as exc:
            raise TTSError(
                f"Failed to load OmniVoice model: {exc}",
                provider=self.name,
                recoverable=False,
            ) from exc
        finally:
            self._model_loading = False

    def _load_model_sync(self):
        return OmniVoice.from_pretrained(
            "k2-fsa/OmniVoice",
            device_map=self.device,
            dtype=self.dtype,
        )

    def _build_generate_kwargs(self, text: str) -> dict:
        if not text.strip():
            raise TTSError("Cannot synthesize empty text", provider=self.name)

        kwargs = {
            "text": text,
            "num_step": self.omnivoice_num_step,
            "speed": self.omnivoice_speed,
        }

        if self.omnivoice_duration is not None:
            kwargs["duration"] = self.omnivoice_duration

        if self.omnivoice_mode == "voice_design":
            if not self.omnivoice_instruct.strip():
                raise TTSError(
                    "OmniVoice voice design mode requires an instruction prompt",
                    provider=self.name,
                )
            kwargs["instruct"] = self.omnivoice_instruct
        elif self.omnivoice_mode == "voice_cloning":
            if not self.omnivoice_ref_audio_path:
                raise TTSError(
                    "OmniVoice voice cloning mode requires a reference audio path",
                    provider=self.name,
                )
            if not Path(self.omnivoice_ref_audio_path).exists():
                raise TTSError(
                    f"Reference audio file not found: {self.omnivoice_ref_audio_path}",
                    provider=self.name,
                )
            kwargs["ref_audio"] = self.omnivoice_ref_audio_path
            if self.omnivoice_ref_text.strip():
                kwargs["ref_text"] = self.omnivoice_ref_text

        return kwargs

    def _audio_to_wav_bytes(self, audio_output) -> bytes:
        if not SOUNDFILE_AVAILABLE:
            raise TTSError(
                "soundfile is required to serialize OmniVoice audio output",
                provider=self.name,
                recoverable=False,
            )

        if isinstance(audio_output, list):
            if not audio_output:
                raise TTSError("OmniVoice returned no audio data", provider=self.name)
            audio_output = audio_output[0]

        if hasattr(audio_output, "cpu"):
            audio_output = audio_output.cpu().numpy()

        buffer = io.BytesIO()
        sf.write(buffer, audio_output, DEFAULT_SAMPLE_RATE, format="WAV")
        buffer.seek(0)
        return buffer.read()

    async def synthesize(
        self,
        text: str,
        voice: str,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ) -> bytes:
        del voice, rate, volume, pitch

        await self._load_model()
        loop = asyncio.get_running_loop()

        try:
            audio_output = await loop.run_in_executor(
                None,
                lambda: self._model.generate(**self._build_generate_kwargs(text)),
            )
            return await loop.run_in_executor(None, self._audio_to_wav_bytes, audio_output)
        except TTSError:
            raise
        except Exception as exc:
            raise TTSError(
                f"OmniVoice synthesis failed: {exc}",
                provider=self.name,
                recoverable=True,
            ) from exc

    async def synthesize_to_file(
        self,
        text: str,
        output_path: str,
        voice: str,
        rate: str = "+0%",
        volume: str = "+0%",
        pitch: str = "+0Hz",
    ) -> TTSResult:
        try:
            audio_data = await self.synthesize(text, voice, rate, volume, pitch)
            Path(output_path).write_bytes(audio_data)
            return TTSResult(success=True, output_path=output_path, audio_data=audio_data)
        except TTSError as exc:
            return TTSResult(success=False, error_message=str(exc))

    async def get_available_voices(self, language_filter: Optional[str] = None) -> List[VoiceInfo]:
        del language_filter
        return [
            VoiceInfo(
                name="omnivoice-auto",
                short_name="Auto",
                language="multi",
                gender="Neutral",
                locale="OmniVoice automatic voice selection",
            ),
            VoiceInfo(
                name="omnivoice-design",
                short_name="Design",
                language="multi",
                gender="Neutral",
                locale="OmniVoice voice design mode",
            ),
            VoiceInfo(
                name="omnivoice-cloning",
                short_name="Cloning",
                language="multi",
                gender="Neutral",
                locale="OmniVoice reference-audio cloning mode",
            ),
        ]


def create_omnivoice_provider(**kwargs) -> OmniVoiceProvider:
    """Factory function to create an OmniVoiceProvider instance."""
    return OmniVoiceProvider(**kwargs)


def is_omnivoice_available() -> bool:
    """Check if OmniVoice runtime dependencies are available."""
    return all(
        (
            TORCH_AVAILABLE,
            TORCHAUDIO_AVAILABLE,
            SOUNDFILE_AVAILABLE,
            OMNIVOICE_AVAILABLE,
        )
    )


def get_omnivoice_missing_dependencies() -> List[str]:
    """Return the Python packages still missing for OmniVoice support."""
    missing = []
    if not TORCH_AVAILABLE:
        missing.append("torch")
    if not TORCHAUDIO_AVAILABLE:
        missing.append("torchaudio")
    if not SOUNDFILE_AVAILABLE:
        missing.append("soundfile")
    if not OMNIVOICE_AVAILABLE:
        missing.append("omnivoice")
    return missing


def get_omnivoice_install_status() -> dict:
    """Return installation guidance for OmniVoice."""
    available = is_omnivoice_available()
    is_container = Path('/.dockerenv').exists()
    missing = get_omnivoice_missing_dependencies()

    if is_container:
        install_method = "docker-build"
        install_command = "INSTALL_OMNIVOICE=1 docker compose up -d --build"
        auto_install_error = (
            "OmniVoice must be baked into the Docker image. Rebuild and restart the service with INSTALL_OMNIVOICE=1."
        )
    else:
        install_method = "pip"
        install_command = "pip install torch torchaudio omnivoice"
        auto_install_error = (
            "Install OmniVoice and its audio dependencies in this Python environment, "
            "then restart the application."
        )

    return {
        "available": available,
        "is_container": is_container,
        "install_method": install_method,
        "install_command": install_command,
        "auto_install_error": None if available else auto_install_error,
        "missing_dependencies": missing,
    }
