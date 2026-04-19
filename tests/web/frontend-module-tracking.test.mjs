import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';

const criticalFrontendModules = [
    'src/web/static/js/tts/chatterbox-install-help.js',
    'src/web/static/js/ui/runtime-status.js'
];

test('critical frontend helper modules are tracked by git for deployment', () => {
    for (const filePath of criticalFrontendModules) {
        assert.doesNotThrow(
            () => execFileSync('git', ['ls-files', '--error-unmatch', filePath], { stdio: 'pipe' }),
            `${filePath} must be tracked so deployments include it`
        );
    }
});
