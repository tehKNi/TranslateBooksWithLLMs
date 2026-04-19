"""Unit tests for Chatterbox installation guidance."""

from src.tts.providers import chatterbox_tts


class TestChatterboxInstallStatus:
    """Test Chatterbox installation metadata for unavailable environments."""

    def test_container_exposes_docker_rebuild_command(self, monkeypatch):
        """Docker environments should advertise an image rebuild, not runtime pip install."""
        monkeypatch.setattr(chatterbox_tts, "TORCH_AVAILABLE", False)
        monkeypatch.setattr(chatterbox_tts, "CHATTERBOX_AVAILABLE", False)
        monkeypatch.setattr(chatterbox_tts, "TORCHAUDIO_AVAILABLE", False)
        monkeypatch.setattr(
            chatterbox_tts.Path,
            "exists",
            lambda self: str(self) == "/.dockerenv",
        )

        status = chatterbox_tts.get_chatterbox_install_status()

        assert status["available"] is False
        assert status["is_container"] is True
        assert status["install_method"] == "docker-build"
        assert "INSTALL_CHATTERBOX=1" in status["install_command"]
        assert "docker compose build" in status["install_command"]
