import test from 'node:test';
import assert from 'node:assert/strict';
import { buildTTSRequestConfig } from '../../src/web/static/js/tts/tts-request-config.js';

test('buildTTSRequestConfig returns Edge-TTS payload defaults', () => {
    const config = buildTTSRequestConfig({
        ttsEnabled: true,
        ttsProvider: 'edge-tts',
        ttsVoice: 'en-US-JennyNeural',
        ttsRate: '+10%',
        ttsFormat: 'opus',
        ttsBitrate: '64k'
    });

    assert.deepEqual(config, {
        tts_enabled: true,
        tts_provider: 'edge-tts',
        tts_voice: 'en-US-JennyNeural',
        tts_rate: '+10%',
        tts_format: 'opus',
        tts_bitrate: '64k'
    });
});

test('buildTTSRequestConfig returns Chatterbox-only fields when selected', () => {
    const config = buildTTSRequestConfig({
        ttsEnabled: true,
        ttsProvider: 'chatterbox',
        voicePromptPath: 'samples/demo.wav',
        exaggeration: '0.75',
        cfgWeight: '0.35',
        ttsFormat: 'mp3',
        ttsBitrate: '96k'
    });

    assert.deepEqual(config, {
        tts_enabled: true,
        tts_provider: 'chatterbox',
        tts_voice: '',
        tts_rate: '+0%',
        tts_format: 'mp3',
        tts_bitrate: '96k',
        tts_voice_prompt_path: 'samples/demo.wav',
        tts_exaggeration: 0.75,
        tts_cfg_weight: 0.35
    });
});

test('buildTTSRequestConfig falls back to default Chatterbox numeric values for invalid input', () => {
    const config = buildTTSRequestConfig({
        ttsEnabled: true,
        ttsProvider: 'chatterbox',
        exaggeration: '  ',
        cfgWeight: 'invalid'
    });

    assert.deepEqual(config, {
        tts_enabled: true,
        tts_provider: 'chatterbox',
        tts_voice: '',
        tts_rate: '+0%',
        tts_format: 'opus',
        tts_bitrate: '64k',
        tts_voice_prompt_path: '',
        tts_exaggeration: 0.5,
        tts_cfg_weight: 0.5
    });
});
