import test from 'node:test';
import assert from 'node:assert/strict';
import { buildChatterboxInstallHelp } from '../../src/web/static/js/tts/chatterbox-install-help.js';

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
