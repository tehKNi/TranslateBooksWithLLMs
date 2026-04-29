"""
Audio Processor for TTS Generation

Handles text chunking, synthesis orchestration, audio concatenation,
and encoding to Opus format via ffmpeg.
"""
import asyncio
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Callable, Tuple

from .tts_config import TTSConfig, get_voice_for_language
from .providers.base import TTSProvider, TTSError, ProgressCallback
from .providers.edge_tts import EdgeTTSProvider
from .providers.chatterbox_tts import ChatterboxProvider, is_chatterbox_available, MAX_TEXT_LENGTH as CHATTERBOX_MAX_LENGTH
from .providers.omnivoice import create_omnivoice_provider

logger = logging.getLogger(__name__)

# Sentence-ending punctuation for chunking
SENTENCE_ENDINGS = re.compile(r'[.!?。！？…]+[\s\n]*')
PARAGRAPH_BREAK = re.compile(r'\n\s*\n')

LINUX_FFMPEG_INSTALLERS = {
    'apt-get': [
        ['apt-get', 'update'],
        ['apt-get', 'install', '-y', 'ffmpeg'],
    ],
    'dnf': [
        ['dnf', 'install', '-y', 'ffmpeg'],
    ],
    'pacman': [
        ['pacman', '-Sy', '--noconfirm', 'ffmpeg'],
    ],
    'apk': [
        ['apk', 'add', '--no-cache', 'ffmpeg'],
    ],
}


def check_ffmpeg_available() -> bool:
    """Check if ffmpeg is available in the system PATH"""
    return shutil.which('ffmpeg') is not None


def _is_root_user() -> bool:
    """Return True when the current process runs with root privileges."""
    geteuid = getattr(os, 'geteuid', None)
    return callable(geteuid) and geteuid() == 0


def _has_passwordless_sudo() -> bool:
    """Return True when sudo can run non-interactively."""
    if shutil.which('sudo') is None:
        return False

    try:
        result = subprocess.run(
            ['sudo', '-n', 'true'],
            capture_output=True,
            text=True,
            timeout=5
        )
    except (subprocess.SubprocessError, OSError):
        return False

    return result.returncode == 0


def _prefix_commands(commands: List[List[str]], prefix: List[str]) -> List[List[str]]:
    """Prefix each command with the provided executable sequence."""
    return [prefix + command for command in commands]


def _format_commands(commands: List[List[str]]) -> Optional[str]:
    """Format multiple shell commands as a readable string."""
    if not commands:
        return None
    return " && ".join(" ".join(command) for command in commands)


def _get_linux_ffmpeg_install_plan() -> dict:
    """Build Linux installation metadata for FFmpeg."""
    for install_method, commands in LINUX_FFMPEG_INSTALLERS.items():
        if shutil.which(install_method) is None:
            continue

        if _is_root_user():
            auto_install_commands = commands
            install_command = _format_commands(commands)
            can_auto_install = True
            auto_install_error = None
        elif _has_passwordless_sudo():
            auto_install_commands = _prefix_commands(commands, ['sudo', '-n'])
            install_command = _format_commands(_prefix_commands(commands, ['sudo']))
            can_auto_install = True
            auto_install_error = None
        else:
            auto_install_commands = []
            install_command = _format_commands(_prefix_commands(commands, ['sudo']))
            can_auto_install = False
            auto_install_error = "Automatic installation on Linux requires elevated privileges (root or passwordless sudo)."

        return {
            "install_method": install_method,
            "install_command": install_command,
            "can_auto_install": can_auto_install,
            "auto_install_error": auto_install_error,
            "install_commands": auto_install_commands,
        }

    return {
        "install_method": None,
        "install_command": None,
        "can_auto_install": False,
        "auto_install_error": "No supported Linux package manager was found. Supported: apt-get, dnf, pacman, apk.",
        "install_commands": [],
    }


def _get_ffmpeg_install_plan() -> dict:
    """Build platform-aware FFmpeg installation metadata."""
    import platform

    system = platform.system().lower()
    plan = {
        "platform": system,
        "install_method": None,
        "install_command": None,
        "can_auto_install": False,
        "auto_install_error": None,
        "install_commands": [],
        "is_container": Path('/.dockerenv').exists(),
    }

    if system == "windows":
        winget_available = shutil.which('winget') is not None
        plan.update({
            "install_method": "winget",
            "install_command": "winget install Gyan.FFmpeg",
            "can_auto_install": winget_available,
            "auto_install_error": None if winget_available else "winget is not available. Please install FFmpeg manually.",
        })
    elif system == "linux":
        plan.update(_get_linux_ffmpeg_install_plan())

    return plan


def get_ffmpeg_install_instructions() -> str:
    """
    Get platform-specific installation instructions for ffmpeg.

    Returns:
        Human-readable installation instructions
    """
    import platform
    system = platform.system().lower()

    instructions = "\n" + "=" * 60 + "\n"
    instructions += "FFmpeg is required for audio encoding but was not found.\n"
    instructions += "=" * 60 + "\n\n"

    if system == "windows":
        instructions += "WINDOWS - Choose one method:\n\n"
        instructions += "Option 1 - WinGet (Recommended, Windows 10/11):\n"
        instructions += "  Open PowerShell/Terminal as Administrator and run:\n"
        instructions += "  > winget install Gyan.FFmpeg\n"
        instructions += "  Then restart your terminal/application.\n\n"
        instructions += "Option 2 - Chocolatey:\n"
        instructions += "  > choco install ffmpeg\n\n"
        instructions += "Option 3 - Manual:\n"
        instructions += "  1. Download from https://ffmpeg.org/download.html\n"
        instructions += "  2. Extract to C:\\ffmpeg\n"
        instructions += "  3. Add C:\\ffmpeg\\bin to your PATH\n"
    elif system == "darwin":
        instructions += "macOS - Using Homebrew:\n"
        instructions += "  $ brew install ffmpeg\n\n"
        instructions += "If you don't have Homebrew:\n"
        instructions += "  $ /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"\n"
    else:  # Linux
        instructions += "LINUX:\n\n"
        instructions += "Ubuntu/Debian:\n"
        instructions += "  $ sudo apt update && sudo apt install ffmpeg\n\n"
        instructions += "Fedora:\n"
        instructions += "  $ sudo dnf install ffmpeg\n\n"
        instructions += "Arch:\n"
        instructions += "  $ sudo pacman -S ffmpeg\n\n"
        instructions += "Alpine:\n"
        instructions += "  $ sudo apk add --no-cache ffmpeg\n\n"
        instructions += "Docker containers:\n"
        instructions += "  If the app runs as root (or has passwordless sudo), the web UI can install FFmpeg automatically.\n"

    instructions += "\n" + "-" * 60 + "\n"
    instructions += "After installation, restart your terminal/application.\n"
    instructions += "=" * 60 + "\n"

    return instructions


def check_ffmpeg_with_instructions() -> Tuple[bool, str]:
    """
    Check if ffmpeg is available and return installation instructions if not.

    Returns:
        Tuple of (is_available: bool, message: str)
        - If available: (True, "ffmpeg found: <version>")
        - If not: (False, "<installation instructions>")
    """
    if check_ffmpeg_available():
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            version_line = result.stdout.split('\n')[0] if result.stdout else "unknown version"
            return True, f"ffmpeg found: {version_line}"
        except Exception:
            return True, "ffmpeg found"

    return False, get_ffmpeg_install_instructions()


def get_ffmpeg_status() -> dict:
    """
    Get detailed FFmpeg status for API responses.

    Returns:
        Dict with availability status and version info
    """
    available = check_ffmpeg_available()
    install_plan = _get_ffmpeg_install_plan()
    result = {
        "available": available,
        "platform": install_plan["platform"],
        "version": None,
        "can_auto_install": install_plan["can_auto_install"],
        "install_method": install_plan["install_method"],
        "install_command": install_plan["install_command"],
        "auto_install_error": install_plan["auto_install_error"],
        "is_container": install_plan["is_container"],
    }

    if available:
        try:
            proc = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            if proc.stdout:
                result["version"] = proc.stdout.split('\n')[0]
        except Exception:
            result["version"] = "unknown"

    return result


def install_ffmpeg_windows() -> Tuple[bool, str]:
    """
    Attempt to install FFmpeg on Windows using winget.

    Returns:
        Tuple of (success: bool, message: str)
    """
    import platform
    if platform.system().lower() != "windows":
        return False, "Auto-installation is only supported on Windows"

    logger.info("Attempting to install FFmpeg via winget...")

    try:
        # Check if winget is available
        winget_check = subprocess.run(
            ['winget', '--version'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if winget_check.returncode != 0:
            return False, "winget is not available. Please install FFmpeg manually."

        # Install FFmpeg using winget
        result = subprocess.run(
            ['winget', 'install', 'Gyan.FFmpeg', '--accept-package-agreements', '--accept-source-agreements'],
            capture_output=True,
            text=True,
            timeout=300  # 5 minutes timeout for download/install
        )

        if result.returncode == 0:
            logger.info("FFmpeg installed successfully via winget")
            return True, "FFmpeg installed successfully! Please restart the application to use TTS."
        else:
            # Check if already installed
            if "already installed" in result.stdout.lower() or "already installed" in result.stderr.lower():
                return True, "FFmpeg is already installed. Please restart the application."

            error_msg = result.stderr or result.stdout or "Unknown error"
            logger.error(f"winget install failed: {error_msg}")
            return False, f"Installation failed: {error_msg}"

    except subprocess.TimeoutExpired:
        return False, "Installation timed out. Please try installing FFmpeg manually."
    except FileNotFoundError:
        return False, "winget not found. Please install FFmpeg manually or install winget first."
    except Exception as e:
        logger.exception("Error during FFmpeg installation")
        return False, f"Installation error: {str(e)}"


def install_ffmpeg_linux() -> Tuple[bool, str]:
    """
    Attempt to install FFmpeg on Linux using the detected package manager.

    Returns:
        Tuple of (success: bool, message: str)
    """
    import platform

    if platform.system().lower() != "linux":
        return False, "Auto-installation is only supported on Linux"

    install_plan = _get_ffmpeg_install_plan()
    if not install_plan["install_method"]:
        return False, install_plan["auto_install_error"] or "No supported Linux package manager was found."
    if not install_plan["can_auto_install"]:
        return False, install_plan["auto_install_error"] or "Automatic installation is not available on this Linux system."

    logger.info("Attempting to install FFmpeg via %s...", install_plan["install_method"])

    try:
        for command in install_plan["install_commands"]:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300
            )
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout or "Unknown error"
                logger.error("%s command failed: %s", install_plan["install_method"], error_msg)
                return False, f"Installation failed: {error_msg}"

        logger.info("FFmpeg installed successfully via %s", install_plan["install_method"])
        return True, "FFmpeg installed successfully! Please restart the application to use TTS."
    except subprocess.TimeoutExpired:
        return False, "Installation timed out. Please try installing FFmpeg manually."
    except FileNotFoundError:
        return False, f"{install_plan['install_method']} not found. Please install FFmpeg manually."
    except Exception as e:
        logger.exception("Error during FFmpeg installation")
        return False, f"Installation error: {str(e)}"


def install_ffmpeg() -> Tuple[bool, str]:
    """
    Attempt to install FFmpeg using the best installer available for this platform.

    Returns:
        Tuple of (success: bool, message: str)
    """
    import platform

    system = platform.system().lower()
    if system == "windows":
        return install_ffmpeg_windows()
    if system == "linux":
        return install_ffmpeg_linux()
    return False, "Auto-installation is only supported on Windows and Linux"


def chunk_text_for_tts(text: str, max_chunk_size: int = 5000) -> List[str]:
    """
    Split text into chunks suitable for TTS synthesis.

    Respects sentence boundaries to avoid cutting words mid-sentence.
    Aims for natural pauses at paragraph and sentence breaks.

    Args:
        text: Full text to chunk
        max_chunk_size: Maximum characters per chunk

    Returns:
        List of text chunks
    """
    if not text.strip():
        return []

    # Normalize whitespace
    text = text.strip()

    # If text is small enough, return as single chunk
    if len(text) <= max_chunk_size:
        return [text]

    chunks = []
    current_chunk = ""

    # Split by paragraphs first
    paragraphs = PARAGRAPH_BREAK.split(text)

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        # If paragraph fits in current chunk, add it
        if len(current_chunk) + len(paragraph) + 2 <= max_chunk_size:
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += paragraph
        else:
            # Paragraph doesn't fit - need to split by sentences
            if current_chunk:
                chunks.append(current_chunk)
                current_chunk = ""

            # If single paragraph is too long, split by sentences
            if len(paragraph) > max_chunk_size:
                sentences = SENTENCE_ENDINGS.split(paragraph)
                sentence_ends = SENTENCE_ENDINGS.findall(paragraph)

                for i, sentence in enumerate(sentences):
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    # Add back the punctuation
                    if i < len(sentence_ends):
                        sentence += sentence_ends[i].strip()

                    if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
                        if current_chunk:
                            current_chunk += " "
                        current_chunk += sentence
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        # If single sentence is too long, force split
                        if len(sentence) > max_chunk_size:
                            for j in range(0, len(sentence), max_chunk_size):
                                chunks.append(sentence[j:j + max_chunk_size])
                            current_chunk = ""
                        else:
                            current_chunk = sentence
            else:
                current_chunk = paragraph

    # Don't forget the last chunk
    if current_chunk:
        chunks.append(current_chunk)

    return chunks


class AudioProcessor:
    """
    Orchestrates TTS generation for complete documents.

    Handles:
    - Text chunking optimized for TTS
    - Chunk-by-chunk synthesis with progress callbacks
    - Audio concatenation
    - Opus encoding via ffmpeg
    """

    def __init__(self, config: TTSConfig, provider: Optional[TTSProvider] = None):
        """
        Initialize the AudioProcessor.

        Args:
            config: TTS configuration
            provider: TTS provider instance (defaults to EdgeTTSProvider)
        """
        self.config = config
        self.provider = provider or EdgeTTSProvider()
        self._temp_dir: Optional[Path] = None
        self._intermediate_extension = self._get_intermediate_extension()

        # Adjust chunk size based on provider
        # Chatterbox has strict tokenizer limits
        if isinstance(self.provider, ChatterboxProvider):
            # Use smaller chunks for Chatterbox (with safety margin)
            self._effective_chunk_size = min(config.chunk_size, CHATTERBOX_MAX_LENGTH - 50)
            logger.info(f"Using Chatterbox-optimized chunk size: {self._effective_chunk_size}")
        else:
            self._effective_chunk_size = config.chunk_size

    def _get_intermediate_extension(self) -> str:
        """Return the temp audio file extension used by the current provider."""
        if isinstance(self.provider, EdgeTTSProvider):
            return '.mp3'
        return '.wav'

    def _requires_ffmpeg(self, total_chunks: int) -> bool:
        """Return True when final assembly/transcoding requires ffmpeg."""
        output_format = self.config.output_format.lower()

        if output_format == 'opus':
            return True

        if self._intermediate_extension == '.mp3':
            return total_chunks > 1

        return output_format != 'wav' or total_chunks > 1

    async def generate_audio(
        self,
        text: str,
        output_path: str,
        language: str = "",
        progress_callback: Optional[ProgressCallback] = None
    ) -> Tuple[bool, str]:
        """
        Generate audio from text and save to output file.

        Args:
            text: Text to convert to speech
            output_path: Destination path for audio file
            language: Target language for voice selection
            progress_callback: Optional callback(current, total, message)

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not text.strip():
            return False, "No text provided for TTS generation"

        try:
            # Create temp directory for intermediate files
            self._temp_dir = Path(tempfile.mkdtemp(prefix="tts_"))

            # Chunk the text (use provider-appropriate chunk size)
            chunks = chunk_text_for_tts(text, self._effective_chunk_size)
            total_chunks = len(chunks)

            if total_chunks == 0:
                return False, "Text produced no chunks for synthesis"

            # Determine voice
            voice = self.config.get_effective_voice(language)
            if getattr(self.provider, 'name', '') == 'omnivoice':
                voice = self.config.voice or 'omnivoice'

            if not voice:
                return False, f"Could not determine voice for language: {language}"

            logger.info(f"Starting TTS generation with voice: {voice}")

            if self._requires_ffmpeg(total_chunks):
                ffmpeg_available, ffmpeg_message = check_ffmpeg_with_instructions()
                if not ffmpeg_available:
                    return False, ffmpeg_message

            logger.info(f"Text split into {total_chunks} chunks")

            # Synthesize each chunk
            temp_audio_files: List[Path] = []

            for i, chunk in enumerate(chunks):
                if progress_callback:
                    progress_callback(i + 1, total_chunks, f"Synthesizing chunk {i + 1}/{total_chunks}")

                # Generate temp file path for this chunk
                temp_file = self._temp_dir / f"chunk_{i:04d}{self._intermediate_extension}"

                # Synthesize
                result = await self.provider.synthesize_to_file(
                    text=chunk,
                    output_path=str(temp_file),
                    voice=voice,
                    rate=self.config.rate,
                    volume=self.config.volume,
                    pitch=self.config.pitch
                )

                if not result.success:
                    return False, f"Failed to synthesize chunk {i + 1}: {result.error_message}"

                temp_audio_files.append(temp_file)

            # Concatenate and encode
            if progress_callback:
                progress_callback(total_chunks, total_chunks, "Concatenating audio...")

            if self.config.output_format.lower() == 'opus':
                success, message = await self._concatenate_and_encode_opus(
                    temp_audio_files,
                    output_path
                )
            elif self._intermediate_extension == '.wav':
                success, message = await self._concatenate_audio_files(
                    temp_audio_files,
                    output_path
                )
            else:
                success, message = await self._concatenate_mp3(
                    temp_audio_files,
                    output_path
                )

            if success:
                logger.info(f"TTS generation complete: {output_path}")

            return success, message

        except TTSError as e:
            return False, str(e)
        except Exception as e:
            logger.exception("Unexpected error during TTS generation")
            return False, f"TTS generation failed: {e}"
        finally:
            # Cleanup temp directory
            self._cleanup_temp()

    async def _concatenate_mp3(
        self,
        input_files: List[Path],
        output_path: str
    ) -> Tuple[bool, str]:
        """
        Concatenate MP3 files without re-encoding.

        Args:
            input_files: List of MP3 files to concatenate
            output_path: Destination path

        Returns:
            Tuple of (success, message)
        """
        if len(input_files) == 1:
            # Just copy the single file
            shutil.copy(input_files[0], output_path)
            return True, "Audio saved successfully"

        try:
            # Create concat file list for ffmpeg
            concat_file = self._temp_dir / "concat.txt"
            with open(concat_file, 'w', encoding='utf-8') as f:
                for audio_file in input_files:
                    # Escape single quotes in path
                    escaped_path = str(audio_file).replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            # Use ffmpeg to concatenate
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c', 'copy',
                output_path
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await result.communicate()

            if result.returncode != 0:
                return False, f"ffmpeg concatenation failed: {stderr.decode()}"

            return True, "Audio concatenated successfully"

        except Exception as e:
            return False, f"MP3 concatenation failed: {e}"

    def _get_ffmpeg_output_args(self) -> List[str]:
        """Return ffmpeg codec arguments for the configured output format."""
        output_format = self.config.output_format.lower()

        if output_format == 'wav':
            return ['-c:a', 'pcm_s16le']
        if output_format == 'mp3':
            return ['-c:a', 'libmp3lame', '-b:a', self.config.bitrate]
        if output_format == 'opus':
            return [
                '-c:a', 'libopus',
                '-b:a', self.config.bitrate,
                '-ar', str(self.config.sample_rate),
                '-ac', '1',
                '-application', 'voip',
            ]
        if output_format == 'ogg':
            return ['-c:a', 'libvorbis', '-b:a', self.config.bitrate]

        raise ValueError(f"Unsupported audio output format: {self.config.output_format}")

    async def _concatenate_audio_files(
        self,
        input_files: List[Path],
        output_path: str
    ) -> Tuple[bool, str]:
        """
        Concatenate or transcode non-MP3 intermediates into the final output format.

        Supports WAV intermediates produced by local providers such as Chatterbox and OmniVoice.
        """
        try:
            output_format = self.config.output_format.lower()

            if len(input_files) == 1 and output_format == 'wav':
                shutil.copy(input_files[0], output_path)
                return True, "Audio saved successfully"

            cmd = ['ffmpeg', '-y']

            if len(input_files) == 1:
                cmd.extend(['-i', str(input_files[0])])
            else:
                concat_file = self._temp_dir / "concat.txt"
                with open(concat_file, 'w', encoding='utf-8') as f:
                    for audio_file in input_files:
                        escaped_path = str(audio_file).replace("'", "'\\''")
                        f.write(f"file '{escaped_path}'\n")

                cmd.extend(['-f', 'concat', '-safe', '0', '-i', str(concat_file)])

            cmd.extend(self._get_ffmpeg_output_args())
            cmd.append(output_path)

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await result.communicate()

            if result.returncode != 0:
                return False, f"Audio concatenation failed: {stderr.decode()}"

            return True, "Audio saved successfully"

        except Exception as e:
            return False, f"Audio concatenation failed: {e}"

    async def _concatenate_and_encode_opus(
        self,
        input_files: List[Path],
        output_path: str
    ) -> Tuple[bool, str]:
        """
        Concatenate MP3 files and encode to Opus.

        Args:
            input_files: List of MP3 files to concatenate
            output_path: Destination path for Opus file

        Returns:
            Tuple of (success, message)
        """
        try:
            # Create concat file list
            concat_file = self._temp_dir / "concat.txt"
            with open(concat_file, 'w', encoding='utf-8') as f:
                for audio_file in input_files:
                    escaped_path = str(audio_file).replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            # ffmpeg command to concat and encode to opus
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', str(concat_file),
                '-c:a', 'libopus',
                '-b:a', self.config.bitrate,
                '-ar', str(self.config.sample_rate),
                '-ac', '1',  # Mono for speech
                '-application', 'voip',  # Optimized for speech
                output_path
            ]

            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await result.communicate()

            if result.returncode != 0:
                return False, f"Opus encoding failed: {stderr.decode()}"

            return True, "Audio encoded to Opus successfully"

        except Exception as e:
            return False, f"Opus encoding failed: {e}"

    def _cleanup_temp(self):
        """Remove temporary directory and files"""
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
            except Exception as e:
                logger.warning(f"Failed to cleanup temp directory: {e}")
            self._temp_dir = None


def create_tts_provider(provider_name: str = "edge-tts", **kwargs) -> TTSProvider:
    """
    Factory function to create a TTS provider.

    Args:
        provider_name: Name of the provider to create
        **kwargs: Additional arguments for provider (e.g., voice_prompt_path for chatterbox)

    Returns:
        TTSProvider instance

    Raises:
        ValueError: If provider is not supported
    """
    if provider_name == "edge-tts":
        return EdgeTTSProvider()

    elif provider_name == "chatterbox":
        if not is_chatterbox_available():
            raise ValueError(
                "Chatterbox TTS is not available. Install with: "
                "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124 && "
                "pip install chatterbox-tts"
            )
        return ChatterboxProvider(
            voice_prompt_path=kwargs.get('voice_prompt_path'),
            exaggeration=kwargs.get('exaggeration', 0.5),
            cfg_weight=kwargs.get('cfg_weight', 0.5)
        )

    elif provider_name == "omnivoice":
        return create_omnivoice_provider(
            omnivoice_mode=kwargs.get('omnivoice_mode', 'auto'),
            omnivoice_ref_audio_path=kwargs.get('omnivoice_ref_audio_path', ''),
            omnivoice_ref_text=kwargs.get('omnivoice_ref_text', ''),
            omnivoice_instruct=kwargs.get('omnivoice_instruct', ''),
            omnivoice_speed=kwargs.get('omnivoice_speed', 1.0),
            omnivoice_duration=kwargs.get('omnivoice_duration'),
            omnivoice_num_step=kwargs.get('omnivoice_num_step', 32),
        )

    else:
        supported = ["edge-tts"]
        if is_chatterbox_available():
            supported.append("chatterbox")
        supported.append("omnivoice")
        raise ValueError(f"Unknown TTS provider: {provider_name}. Supported: {supported}")


async def generate_tts_for_text(
    text: str,
    output_path: str,
    config: Optional[TTSConfig] = None,
    language: str = "",
    progress_callback: Optional[ProgressCallback] = None
) -> Tuple[bool, str]:
    """
    High-level function to generate TTS audio from text.

    Args:
        text: Text to convert to speech
        output_path: Destination path for audio file
        config: TTS configuration (uses defaults if None)
        language: Target language for voice selection
        progress_callback: Optional progress callback

    Returns:
        Tuple of (success: bool, message: str)
    """
    if config is None:
        config = TTSConfig.from_env()
        config.target_language = language

    provider = create_tts_provider(
        config.provider,
        voice_prompt_path=config.voice_prompt_path,
        exaggeration=config.exaggeration,
        cfg_weight=config.cfg_weight,
        omnivoice_mode=config.omnivoice_mode,
        omnivoice_ref_audio_path=config.omnivoice_ref_audio_path,
        omnivoice_ref_text=config.omnivoice_ref_text,
        omnivoice_instruct=config.omnivoice_instruct,
        omnivoice_speed=config.omnivoice_speed,
        omnivoice_duration=config.omnivoice_duration,
        omnivoice_num_step=config.omnivoice_num_step,
    )
    processor = AudioProcessor(config, provider)

    return await processor.generate_audio(
        text=text,
        output_path=output_path,
        language=language,
        progress_callback=progress_callback
    )
