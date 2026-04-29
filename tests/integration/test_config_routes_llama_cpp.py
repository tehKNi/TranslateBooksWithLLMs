"""Integration tests for llama.cpp config route exposure."""

from flask import Flask

from src.api.blueprints.config_routes import create_config_blueprint


def test_config_endpoint_exposes_llama_cpp_defaults():
    """The config endpoint should publish llama.cpp defaults for the UI."""
    app = Flask(__name__)
    app.register_blueprint(create_config_blueprint(server_session_id=123456))

    with app.test_client() as client:
        response = client.get("/api/config")

    assert response.status_code == 200
    payload = response.get_json()

    assert payload["llama_cpp_api_endpoint"] == "http://localhost:8080/v1/chat/completions"
    assert "llama_cpp_default_model" in payload
