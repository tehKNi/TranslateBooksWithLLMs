import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

test('index.js does not statically import the chatterbox helper module', () => {
    const source = readFileSync('src/web/static/js/index.js', 'utf8');

    assert.doesNotMatch(
        source,
        /import\s+\{\s*buildChatterboxInstallHelp\s*\}\s+from\s+'\.\/tts\/chatterbox-install-help\.js';/,
        'index.js must not hard-fail when the chatterbox helper file is missing during deployment'
    );
});

test('lifecycle-manager does not statically import the runtime-status helper module', () => {
    const source = readFileSync('src/web/static/js/utils/lifecycle-manager.js', 'utf8');

    assert.doesNotMatch(
        source,
        /import\s+\{\s*renderRuntimeStatus\s*\}\s+from\s+'\.\.\/ui\/runtime-status\.js';/,
        'lifecycle-manager must not hard-fail when the runtime-status helper file is missing during deployment'
    );
});
