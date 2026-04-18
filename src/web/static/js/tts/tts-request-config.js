function parseFloatOrDefault(value, fallback) {
    const parsedValue = Number.parseFloat(value);
    return Number.isNaN(parsedValue) ? fallback : parsedValue;
}

export function buildTTSRequestConfig({
    ttsEnabled = false,
    ttsProvider = 'edge-tts',
    ttsVoice = '',
    ttsRate = '+0%',
    ttsFormat = 'opus',
    ttsBitrate = '64k',
    voicePromptPath = '',
    exaggeration = '0.5',
    cfgWeight = '0.5'
} = {}) {
    if (!ttsEnabled) {
        return {
            tts_enabled: false,
            tts_provider: 'edge-tts',
            tts_voice: '',
            tts_rate: '+0%',
            tts_format: 'opus',
            tts_bitrate: '64k'
        };
    }

    const config = {
        tts_enabled: true,
        tts_provider: ttsProvider || 'edge-tts',
        tts_voice: ttsProvider === 'chatterbox' ? '' : (ttsVoice || ''),
        tts_rate: ttsRate || '+0%',
        tts_format: ttsFormat || 'opus',
        tts_bitrate: ttsBitrate || '64k'
    };

    if (config.tts_provider === 'chatterbox') {
        config.tts_voice_prompt_path = voicePromptPath || '';
        config.tts_exaggeration = parseFloatOrDefault(exaggeration, 0.5);
        config.tts_cfg_weight = parseFloatOrDefault(cfgWeight, 0.5);
    }

    return config;
}
