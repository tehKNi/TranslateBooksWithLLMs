"""Unit tests for startup/runtime health metadata."""

from flask import Flask

from src.api.blueprints.config_routes import create_config_blueprint


def test_health_check_exposes_runtime_and_tts_metadata():
    """The health endpoint should expose visible runtime/build and TTS install status."""
    app = Flask(__name__)
    app.register_blueprint(create_config_blueprint(server_session_id=123456))

    with app.test_client() as client:
        response = client.get('/api/health')

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["runtime"]["session_id"] == 123456
    assert "version_display" in payload["runtime"]
    assert "is_container" in payload["runtime"]
    assert payload["tts"]["chatterbox"]["available"] in (True, False)
    assert "install_method" in payload["tts"]["chatterbox"]["install"]
