import test from 'node:test';
import assert from 'node:assert/strict';
import {
    buildChatterboxInstallHelp,
    buildOmniVoiceInstallHelp
} from '../../src/web/static/js/tts/chatterbox-install-help.js';

test('buildChatterboxInstallHelp renders docker rebuild guidance for container installs', () => {
    const html = buildChatterboxInstallHelp({
        available: false,
        install_method: 'docker-build',
        install_command: 'INSTALL_CHATTERBOX=1 docker compose up -d --build',
        auto_install_error: 'Chatterbox must be baked into the Docker image. Rebuild and restart the service with INSTALL_CHATTERBOX=1.',
        is_container: true
    });

    assert.match(html, /INSTALL_CHATTERBOX=1/);
    assert.match(html, /Copy Docker rebuild command/);
    assert.match(html, /baked into the docker image/i);
});

test('buildOmniVoiceInstallHelp renders docker rebuild guidance for container installs', () => {
    const html = buildOmniVoiceInstallHelp({
        available: false,
        install_method: 'docker-build',
        install_command: 'INSTALL_OMNIVOICE=1 docker compose up -d --build',
        auto_install_error: 'OmniVoice must be baked into the Docker image. Rebuild and restart the service with INSTALL_OMNIVOICE=1.',
        is_container: true
    });

    assert.match(html, /INSTALL_OMNIVOICE=1/);
    assert.match(html, /OmniVoice is not installed in this Docker image/i);
    assert.match(html, /Copy Docker rebuild command/);
});
