import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('post-translation TTS modal exposes OmniVoice provider and install help wiring', async () => {
    const source = await readFile(
        new URL('../../src/web/static/js/index.js', import.meta.url),
        'utf8'
    );

    assert.match(source, /<option value="omnivoice"/);
    assert.match(source, /ttsModalOmniVoiceOptions/);
    assert.match(source, /ttsModalOmniVoiceInstallHelp/);
    assert.match(source, /tts_omnivoice_mode/);
    assert.match(source, /providersInfo\.omnivoice/);
});
