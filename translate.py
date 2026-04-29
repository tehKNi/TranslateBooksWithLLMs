"""
Command-line interface for text translation.
"""

import argparse
import asyncio
import logging
import os
import uuid

# Reduce verbosity of httpx (avoid showing 400 errors during model detection)
logging.getLogger('httpx').setLevel(logging.WARNING)

from src.config import (  # noqa: E402
    API_ENDPOINT,
    DEFAULT_MODEL,
    DEFAULT_SOURCE_LANGUAGE,
    DEFAULT_TARGET_LANGUAGE,
    DEEPSEEK_API_KEY,
    GEMINI_API_KEY,
    LLAMA_CPP_API_ENDPOINT,
    LLAMA_CPP_MODEL,
    LLM_PROVIDER,
    MISTRAL_API_KEY,
    NIM_API_KEY,
    OPENAI_API_KEY,
    OPENROUTER_API_KEY,
    POE_API_KEY,
)
from src.persistence.checkpoint_manager import CheckpointManager  # noqa: E402
from src.core.adapters import translate_file  # noqa: E402
from src.tts.tts_config import (  # noqa: E402
    TTS_BITRATE,
    TTS_ENABLED,
    TTS_OUTPUT_FORMAT,
    TTS_PROVIDER,
    TTS_RATE,
    TTS_VOICE,
    TTSConfig,
)
from src.tts.providers import (  # noqa: E402
    get_chatterbox_install_status,
    get_omnivoice_install_status,
    is_chatterbox_available,
    is_omnivoice_available,
)
from src.utils.file_utils import generate_tts_for_translation, get_unique_output_path  # noqa: E402
from src.utils.unified_logger import LogType, setup_cli_logger  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Translate a text, EPUB or SRT file using an LLM.")
    parser.add_argument("-i", "--input", required=True, help="Path to the input file (text, EPUB, or SRT).")
    parser.add_argument("-o", "--output", default=None, help="Path to the output file. If not specified, uses input filename with suffix.")
    parser.add_argument("-sl", "--source_lang", default=DEFAULT_SOURCE_LANGUAGE, help=f"Source language (default: {DEFAULT_SOURCE_LANGUAGE}).")
    parser.add_argument("-tl", "--target_lang", default=DEFAULT_TARGET_LANGUAGE, help=f"Target language (default: {DEFAULT_TARGET_LANGUAGE}).")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"LLM model (default: {DEFAULT_MODEL}).")
    parser.add_argument("--api_endpoint", default=API_ENDPOINT, help=f"API endpoint for Ollama, llama.cpp, or OpenAI-compatible servers (default: {API_ENDPOINT}).")
    parser.add_argument("--provider", default=LLM_PROVIDER, choices=["ollama", "llama_cpp", "gemini", "openai", "openrouter", "mistral", "deepseek", "poe", "nim"], help=f"LLM provider (default: {LLM_PROVIDER}). Use 'llama_cpp' for llama-server or 'openai' for generic OpenAI-compatible endpoints.")
    parser.add_argument("--gemini_api_key", default=GEMINI_API_KEY, help="Google Gemini API key (required if using gemini provider).")
    parser.add_argument("--openai_api_key", default=OPENAI_API_KEY, help="OpenAI API key (required for OpenAI cloud, not needed for local servers).")
    parser.add_argument("--openrouter_api_key", default=OPENROUTER_API_KEY, help="OpenRouter API key (required if using openrouter provider).")
    parser.add_argument("--mistral_api_key", default=MISTRAL_API_KEY, help="Mistral API key (required if using mistral provider).")
    parser.add_argument("--deepseek_api_key", default=DEEPSEEK_API_KEY, help="DeepSeek API key (required if using deepseek provider).")
    parser.add_argument("--poe_api_key", default=POE_API_KEY, help="Poe API key (required if using poe provider). Get your key at https://poe.com/api_key")
    parser.add_argument("--nim_api_key", default=NIM_API_KEY, help="NVIDIA NIM API key (required if using nim provider). Get your key at https://build.nvidia.com/")
    parser.add_argument("--no-color", action="store_true", help="Disable colored output.")

    prompt_group = parser.add_argument_group('Prompt Options', 'Optional instructions to include in the translation prompt')
    prompt_group.add_argument("--text-cleanup", action="store_true", help="Enable OCR/typographic cleanup (fix broken lines, spacing, punctuation).")
    prompt_group.add_argument("--refine", action="store_true", help="Enable refinement pass: runs a second pass to polish translation quality and literary style.")

    tts_group = parser.add_argument_group('TTS Options', 'Text-to-Speech audio generation')
    tts_group.add_argument("--tts", action="store_true", default=TTS_ENABLED, help="Generate audio from translated text using the selected TTS provider.")
    tts_group.add_argument("--tts-provider", default=TTS_PROVIDER, choices=["edge-tts", "chatterbox", "omnivoice"], help=f"TTS provider (default: {TTS_PROVIDER}).")
    tts_group.add_argument("--tts-voice", default=TTS_VOICE, help="TTS voice name (auto-selected based on target language if not specified).")
    tts_group.add_argument("--tts-rate", default=TTS_RATE, help="TTS speech rate adjustment, e.g. '+10%%' or '-20%%' (default: %(default)s).")
    tts_group.add_argument("--tts-bitrate", default=TTS_BITRATE, help="Audio bitrate for encoding, e.g. '64k', '96k' (default: %(default)s).")
    tts_group.add_argument("--tts-format", default=TTS_OUTPUT_FORMAT, choices=["opus", "mp3", "wav"], help="Audio output format (default: %(default)s).")

    omnivoice_group = parser.add_argument_group('OmniVoice Options', 'Options specific to the OmniVoice TTS provider')
    omnivoice_group.add_argument("--omnivoice-mode", default="auto", choices=["auto", "voice_design", "voice_cloning"], help="OmniVoice generation mode.")
    omnivoice_group.add_argument("--omnivoice-instruct", default="", help="Text instruction for OmniVoice voice design mode.")
    omnivoice_group.add_argument("--omnivoice-ref-audio", default="", help="Reference audio path for OmniVoice voice cloning mode.")
    omnivoice_group.add_argument("--omnivoice-ref-text", default="", help="Optional transcript for the OmniVoice reference audio.")
    omnivoice_group.add_argument("--omnivoice-speed", default=1.0, type=float, help="OmniVoice speed factor (default: %(default)s).")
    omnivoice_group.add_argument("--omnivoice-duration", default=None, type=float, help="Optional fixed output duration in seconds.")
    omnivoice_group.add_argument("--omnivoice-num-step", default=32, type=int, help="OmniVoice diffusion steps (default: %(default)s).")

    return parser


def validate_cli_args(parser: argparse.ArgumentParser, args) -> None:
    """Validate provider-specific CLI requirements."""
    if args.provider == "gemini" and not args.gemini_api_key:
        parser.error("--gemini_api_key is required when using gemini provider")
    if args.provider == "openrouter" and not args.openrouter_api_key:
        parser.error("--openrouter_api_key is required when using openrouter provider")
    if args.provider == "mistral" and not args.mistral_api_key:
        parser.error("--mistral_api_key is required when using mistral provider")
    if args.provider == "deepseek" and not args.deepseek_api_key:
        parser.error("--deepseek_api_key is required when using deepseek provider")
    if args.provider == "poe" and not args.poe_api_key:
        parser.error("--poe_api_key is required when using poe provider. Get your key at https://poe.com/api_key")
    if args.provider == "nim" and not args.nim_api_key:
        parser.error("--nim_api_key is required when using nim provider. Get your key at https://build.nvidia.com/")

    if not args.tts:
        return

    if args.tts_provider == "chatterbox" and not is_chatterbox_available():
        install_status = get_chatterbox_install_status()
        parser.error(
            "Chatterbox TTS is not available. "
            f"Missing dependencies: {', '.join(install_status.get('missing_dependencies', []))}. "
            f"Install with: {install_status.get('install_command')}"
        )

    if args.tts_provider == "omnivoice":
        if not is_omnivoice_available():
            install_status = get_omnivoice_install_status()
            parser.error(
                "OmniVoice TTS is not available. "
                f"Missing dependencies: {', '.join(install_status.get('missing_dependencies', []))}. "
                f"Install with: {install_status.get('install_command')}"
            )

        if args.omnivoice_mode == "voice_design" and not args.omnivoice_instruct.strip():
            parser.error("--omnivoice-instruct is required when --omnivoice-mode voice_design is selected")

        if args.omnivoice_mode == "voice_cloning" and not args.omnivoice_ref_audio:
            parser.error("--omnivoice-ref-audio is required when --omnivoice-mode voice_cloning is selected")


def _apply_default_model(args) -> None:
    """Auto-select provider-specific default model when needed."""
    from src.config import DEEPSEEK_MODEL, GEMINI_MODEL, MISTRAL_MODEL, NIM_MODEL, OPENROUTER_MODEL, POE_MODEL

    if args.model != DEFAULT_MODEL:
        return

    if args.provider == "nim" and NIM_MODEL:
        args.model = NIM_MODEL
    elif args.provider == "mistral" and MISTRAL_MODEL:
        args.model = MISTRAL_MODEL
    elif args.provider == "deepseek" and DEEPSEEK_MODEL:
        args.model = DEEPSEEK_MODEL
    elif args.provider == "poe" and POE_MODEL:
        args.model = POE_MODEL
    elif args.provider == "openrouter" and OPENROUTER_MODEL:
        args.model = OPENROUTER_MODEL
    elif args.provider == "gemini" and GEMINI_MODEL:
        args.model = GEMINI_MODEL
    elif args.provider == "llama_cpp" and LLAMA_CPP_MODEL:
        args.model = LLAMA_CPP_MODEL


def _apply_default_api_endpoint(args) -> None:
    """Auto-select provider-specific default endpoint when needed."""
    if args.provider == "llama_cpp" and args.api_endpoint == API_ENDPOINT:
        args.api_endpoint = LLAMA_CPP_API_ENDPOINT


def _prepare_output_path(args) -> None:
    """Compute the default output path when the user did not provide one."""
    if args.output is None:
        base, ext = os.path.splitext(args.input)
        output_ext = ext
        if args.input.lower().endswith('.epub'):
            output_ext = '.epub'
        elif args.input.lower().endswith('.srt'):
            output_ext = '.srt'
        args.output = f"{base} ({args.target_lang}){output_ext}"

    args.output = get_unique_output_path(args.output)


def _get_file_type(input_path: str) -> str:
    """Return the translation file type label for logging."""
    if input_path.lower().endswith('.epub'):
        return "EPUB"
    if input_path.lower().endswith('.srt'):
        return "SRT"
    return "TEXT"


def main(argv=None) -> None:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    _apply_default_model(args)
    _apply_default_api_endpoint(args)
    _prepare_output_path(args)
    validate_cli_args(parser, args)

    file_type = _get_file_type(args.input)
    logger = setup_cli_logger(enable_colors=not args.no_color)

    logger.info("Translation Started", LogType.TRANSLATION_START, {
        'source_lang': args.source_lang,
        'target_lang': args.target_lang,
        'file_type': file_type,
        'model': args.model,
        'input_file': args.input,
        'output_file': args.output,
        'api_endpoint': args.api_endpoint,
        'llm_provider': args.provider
    })

    log_callback = logger.create_legacy_callback()

    def stats_callback(stats: dict):
        completed = stats.get('completed_chunks', 0)
        total = stats.get('total_chunks', 0)
        if total > 0:
            logger.update_progress(completed, total)

    prompt_options = {
        'preserve_technical_content': True,
        'text_cleanup': args.text_cleanup,
        'refine': args.refine
    }

    try:
        checkpoint_manager = CheckpointManager()
        translation_id = f"cli_{uuid.uuid4().hex[:8]}"

        asyncio.run(translate_file(
            input_filepath=args.input,
            output_filepath=args.output,
            source_language=args.source_lang,
            target_language=args.target_lang,
            model_name=args.model,
            llm_provider=args.provider,
            checkpoint_manager=checkpoint_manager,
            translation_id=translation_id,
            log_callback=log_callback,
            stats_callback=stats_callback,
            check_interruption_callback=None,
            llm_api_endpoint=args.api_endpoint,
            gemini_api_key=args.gemini_api_key,
            openai_api_key=args.openai_api_key,
            openrouter_api_key=args.openrouter_api_key,
            mistral_api_key=args.mistral_api_key,
            deepseek_api_key=args.deepseek_api_key,
            poe_api_key=args.poe_api_key,
            nim_api_key=args.nim_api_key,
            prompt_options=prompt_options
        ))

        logger.info("Translation Completed Successfully", LogType.TRANSLATION_END, {
            'output_file': args.output
        })

        if args.tts:
            logger.info("Starting TTS Generation", LogType.INFO, {
                'provider': args.tts_provider,
                'voice': args.tts_voice or 'auto',
                'rate': args.tts_rate,
                'format': args.tts_format
            })

            tts_config = TTSConfig.from_cli_args(args)
            success, message, audio_path = asyncio.run(generate_tts_for_translation(
                translated_filepath=args.output,
                target_language=args.target_lang,
                tts_config=tts_config,
                log_callback=log_callback
            ))

            if success:
                logger.info("TTS Generation Completed", LogType.INFO, {
                    'audio_file': audio_path
                })
            else:
                logger.error(f"TTS generation failed: {message}", LogType.ERROR_DETAIL, {
                    'details': message
                })

    except Exception as exc:
        logger.error(f"Translation failed: {str(exc)}", LogType.ERROR_DETAIL, {
            'details': str(exc),
            'input_file': args.input
        })


if __name__ == "__main__":
    main()
