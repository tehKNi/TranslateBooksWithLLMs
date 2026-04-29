"""
TTS Providers Package

Factory functions for creating TTS provider instances.
"""
from .base import TTSProvider, TTSResult, VoiceInfo, TTSError, ProgressCallback
from .edge_tts import EdgeTTSProvider, create_edge_tts_provider
from .chatterbox_tts import (
    ChatterboxProvider,
    create_chatterbox_provider,
    is_chatterbox_available,
    get_chatterbox_install_status,
    get_gpu_status,
    CHATTERBOX_LANGUAGES,
    MAX_TEXT_LENGTH as CHATTERBOX_MAX_TEXT_LENGTH,
    sanitize_text_for_tts,
)
from .omnivoice import (
    OmniVoiceProvider,
    create_omnivoice_provider,
    is_omnivoice_available,
    get_omnivoice_install_status,
)

__all__ = [
    # Base classes
    'TTSProvider',
    'TTSResult',
    'VoiceInfo',
    'TTSError',
    'ProgressCallback',
    # Edge-TTS
    'EdgeTTSProvider',
    'create_edge_tts_provider',
    # Chatterbox TTS
    'ChatterboxProvider',
    'create_chatterbox_provider',
    'is_chatterbox_available',
    'get_chatterbox_install_status',
    'get_gpu_status',
    'CHATTERBOX_LANGUAGES',
    'CHATTERBOX_MAX_TEXT_LENGTH',
    'sanitize_text_for_tts',
    # OmniVoice
    'OmniVoiceProvider',
    'create_omnivoice_provider',
    'is_omnivoice_available',
    'get_omnivoice_install_status',
]


def create_provider(provider_name: str = "edge-tts", **kwargs) -> TTSProvider:
    """
    Factory function to create a TTS provider by name.

    Args:
        provider_name: Name of the provider ("edge-tts", "chatterbox")
        **kwargs: Additional arguments passed to provider constructor
            - For chatterbox: voice_prompt_path, exaggeration, cfg_weight

    Returns:
        TTSProvider instance

    Raises:
        ValueError: If provider is not supported
    """
    if provider_name == "edge-tts":
        return create_edge_tts_provider()

    elif provider_name == "chatterbox":
        return create_chatterbox_provider(
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
            omnivoice_num_step=kwargs.get('omnivoice_num_step', 32)
        )

    else:
        available = "edge-tts, chatterbox, omnivoice"
        raise ValueError(f"Unknown TTS provider: {provider_name}. Available: {available}")
