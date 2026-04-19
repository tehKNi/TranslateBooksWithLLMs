import test from 'node:test';
import assert from 'node:assert/strict';
import { buildChatterboxInstallHelp } from '../../src/web/static/js/tts/chatterbox-install-help.js';

test('buildChatterboxInstallHelp renders docker rebuild guidance for container installs', () => {
    const html = buildChatterboxInstallHelp({
        available: false,
        install_method: 'docker-build',
        install_command: 'docker compose build --build-arg INSTALL_CHATTERBOX=1 && docker compose up -d',
        auto_install_error: 'Chatterbox must be added to the Docker image and the container restarted.',
        is_container: true
    });

    assert.match(html, /INSTALL_CHATTERBOX=1/);
    assert.match(html, /Copy Docker rebuild command/);
    assert.match(html, /container restarted/i);
});
