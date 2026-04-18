"""Unit tests for FFmpeg installation detection and execution."""

from types import SimpleNamespace
import platform

from src.tts import audio_processor


class TestFFmpegStatus:
    """Test FFmpeg status metadata for auto-install flows."""

    def test_linux_apt_root_can_auto_install(self, monkeypatch):
        """Linux with apt-get and root should advertise auto-install."""
        monkeypatch.setattr(audio_processor, "check_ffmpeg_available", lambda: False)
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            audio_processor.shutil,
            "which",
            lambda name: "/usr/bin/apt-get" if name == "apt-get" else None,
        )
        monkeypatch.setattr(audio_processor.os, "geteuid", lambda: 0, raising=False)

        status = audio_processor.get_ffmpeg_status()

        assert status["platform"] == "linux"
        assert status["can_auto_install"] is True
        assert status["install_method"] == "apt-get"
        assert status["install_command"] == "apt-get update && apt-get install -y ffmpeg"

    def test_linux_without_privileges_disables_auto_install(self, monkeypatch):
        """Linux without root or sudo should expose manual-only status."""
        monkeypatch.setattr(audio_processor, "check_ffmpeg_available", lambda: False)
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            audio_processor.shutil,
            "which",
            lambda name: "/usr/bin/apt-get" if name == "apt-get" else None,
        )
        monkeypatch.setattr(audio_processor.os, "geteuid", lambda: 1000, raising=False)

        status = audio_processor.get_ffmpeg_status()

        assert status["platform"] == "linux"
        assert status["can_auto_install"] is False
        assert status["install_method"] == "apt-get"
        assert "privilege" in status["auto_install_error"].lower()


class TestFFmpegInstall:
    """Test FFmpeg auto-install command execution."""

    def test_install_ffmpeg_linux_apt_runs_update_then_install(self, monkeypatch):
        """Linux apt auto-install should run apt-get update then install."""
        commands = []

        def fake_run(cmd, capture_output=True, text=True, timeout=None):
            commands.append(cmd)
            return SimpleNamespace(returncode=0, stdout="", stderr="")

        monkeypatch.setattr(audio_processor, "check_ffmpeg_available", lambda: False)
        monkeypatch.setattr(platform, "system", lambda: "Linux")
        monkeypatch.setattr(
            audio_processor.shutil,
            "which",
            lambda name: "/usr/bin/apt-get" if name == "apt-get" else None,
        )
        monkeypatch.setattr(audio_processor.os, "geteuid", lambda: 0, raising=False)
        monkeypatch.setattr(audio_processor.subprocess, "run", fake_run)

        success, message = audio_processor.install_ffmpeg()

        assert success is True
        assert "successfully" in message.lower()
        assert commands == [
            ["apt-get", "update"],
            ["apt-get", "install", "-y", "ffmpeg"],
        ]
