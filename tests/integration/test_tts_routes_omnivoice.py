"""Integration tests for OmniVoice exposure in TTS and translation routes."""

from pathlib import Path

from flask import Flask

from src.api.blueprints.translation_routes import create_translation_blueprint
from src.api.blueprints.tts_routes import create_tts_blueprint
from src.api.blueprints import tts_routes


class DummySocketIO:
    """Minimal SocketIO stub for blueprint creation."""

    def emit(self, *args, **kwargs):
        return None


class DummyStateManager:
    """Minimal state manager stub for translation route tests."""

    def __init__(self):
        self.translations = {}

    def create_translation(self, translation_id, config):
        self.translations[translation_id] = config

    def get_translation(self, translation_id):
        return self.translations.get(translation_id)

    def exists(self, translation_id):
        return translation_id in self.translations

    def set_interrupted(self, translation_id, interrupted):
        if translation_id in self.translations:
            self.translations[translation_id]["interrupted"] = interrupted


def create_app_with_tts(tmp_path):
    """Create a Flask app with the TTS blueprint only."""
    app = Flask(__name__)
    app.register_blueprint(create_tts_blueprint(str(tmp_path), DummySocketIO()))
    return app


def create_app_with_translation():
    """Create a Flask app with the translation blueprint only."""
    app = Flask(__name__)
    state_manager = DummyStateManager()
    started_jobs = []

    def start_translation_job(translation_id, config):
        started_jobs.append((translation_id, config))

    app.register_blueprint(create_translation_blueprint(state_manager, start_translation_job))
    return app


def test_tts_providers_route_lists_omnivoice(monkeypatch, tmp_path):
    """The TTS providers endpoint should advertise OmniVoice capabilities."""
    app = create_app_with_tts(tmp_path)
    client = app.test_client()

    monkeypatch.setattr(
        tts_routes,
        "get_omnivoice_install_status",
        lambda: {
            "available": False,
            "install_method": "pip",
            "install_command": "pip install torch torchaudio omnivoice",
            "missing_dependencies": ["omnivoice"],
        },
        raising=False,
    )

    response = client.get("/api/tts/providers")

    assert response.status_code == 200
    data = response.get_json()
    assert "omnivoice" in data["providers"]
    assert data["providers"]["omnivoice"]["features"]["voice_design"] is True
    assert data["providers"]["omnivoice"]["features"]["voice_cloning"] is True


def test_tts_generate_rejects_unavailable_omnivoice(monkeypatch, tmp_path):
    """The TTS generation endpoint should fail clearly when OmniVoice is unavailable."""
    app = create_app_with_tts(tmp_path)
    client = app.test_client()
    source_file = Path(tmp_path) / "translated.txt"
    source_file.write_text("Hello OmniVoice", encoding="utf-8")

    monkeypatch.setattr(tts_routes, "is_omnivoice_available", lambda: False, raising=False)
    monkeypatch.setattr(
        tts_routes,
        "get_omnivoice_install_status",
        lambda: {
            "available": False,
            "install_method": "pip",
            "install_command": "pip install torch torchaudio omnivoice",
            "missing_dependencies": ["omnivoice"],
        },
        raising=False,
    )

    response = client.post(
        "/api/tts/generate",
        json={
            "filename": "translated.txt",
            "target_language": "English",
            "tts_provider": "omnivoice",
            "tts_omnivoice_mode": "auto",
        },
    )

    assert response.status_code == 400
    data = response.get_json()
    assert "OmniVoice" in data["error"]
    assert data["install"]["missing_dependencies"] == ["omnivoice"]


def test_translate_route_keeps_omnivoice_config():
    """Translation requests should preserve OmniVoice config inside tts_config."""
    app = create_app_with_translation()
    client = app.test_client()

    response = client.post(
        "/api/translate",
        json={
            "text": "Hello world",
            "source_language": "English",
            "target_language": "French",
            "model": "test-model",
            "llm_api_endpoint": "http://localhost:1234/v1/chat/completions",
            "output_filename": "out.txt",
            "tts_enabled": True,
            "tts_provider": "omnivoice",
            "tts_omnivoice_mode": "voice_design",
            "tts_omnivoice_instruct": "female, low pitch",
            "tts_omnivoice_speed": "1.2",
            "tts_omnivoice_num_step": "24",
        },
    )

    assert response.status_code == 200
    data = response.get_json()
    tts_config = data["config_received"]["tts_config"]

    assert tts_config["provider"] == "omnivoice"
    assert tts_config["omnivoice_mode"] == "voice_design"
    assert tts_config["omnivoice_instruct"] == "female, low pitch"
    assert tts_config["omnivoice_speed"] == 1.2
    assert tts_config["omnivoice_num_step"] == 24
