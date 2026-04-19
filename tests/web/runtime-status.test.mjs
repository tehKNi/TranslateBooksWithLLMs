import test from 'node:test';
import assert from 'node:assert/strict';
import { buildRuntimeStatusMarkup } from '../../src/web/static/js/ui/runtime-status.js';

test('buildRuntimeStatusMarkup shows version and chatterbox image guidance', () => {
    const html = buildRuntimeStatusMarkup({
        runtime: {
            version_display: 'main-b059081',
            is_container: true,
            started_at_iso: '2026-04-19T10:00:00Z'
        },
        tts: {
            chatterbox: {
                available: false,
                install: {
                    install_method: 'docker-build',
                    auto_install_error: 'Chatterbox is not baked into the current Docker image.'
                }
            }
        }
    });

    assert.match(html, /main-b059081/);
    assert.match(html, /Chatterbox unavailable/i);
    assert.match(html, /Docker image/i);
});
