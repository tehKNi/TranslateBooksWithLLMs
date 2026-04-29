function parseFloatOrDefault(value, fallback) {
    const parsedValue = Number.parseFloat(value);
    return Number.isNaN(parsedValue) ? fallback : parsedValue;
}

function parseIntOrDefault(value, fallback) {
    const parsedValue = Number.parseInt(value, 10);
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
    cfgWeight = '0.5',
    omnivoiceMode = 'auto',
    omnivoiceInstruct = '',
    omnivoiceRefAudioPath = '',
    omnivoiceRefText = '',
    omnivoiceSpeed = '1.0',
    omnivoiceDuration = '',
    omnivoiceNumStep = '32'
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

    if (config.tts_provider === 'omnivoice') {
        config.tts_voice = '';
        config.tts_omnivoice_mode = omnivoiceMode || 'auto';
        config.tts_omnivoice_instruct = omnivoiceInstruct || '';
        config.tts_omnivoice_ref_audio_path = omnivoiceRefAudioPath || voicePromptPath || '';
        config.tts_omnivoice_ref_text = omnivoiceRefText || '';
        config.tts_omnivoice_speed = parseFloatOrDefault(omnivoiceSpeed, 1.0);
        config.tts_omnivoice_num_step = parseIntOrDefault(omnivoiceNumStep, 32);

        const durationValue = String(omnivoiceDuration ?? '').trim();
        if (durationValue !== '') {
            config.tts_omnivoice_duration = parseFloatOrDefault(durationValue, 0);
        }
    }

    return config;
}
