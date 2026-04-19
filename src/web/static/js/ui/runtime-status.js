function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

function formatStartTime(startedAtIso) {
    if (!startedAtIso) {
        return 'unknown start';
    }

    const date = new Date(startedAtIso);
    if (Number.isNaN(date.getTime())) {
        return 'unknown start';
    }

    return date.toLocaleString();
}

export function buildRuntimeStatusMarkup(healthData = {}) {
    const runtime = healthData.runtime || {};
    const chatterbox = healthData.tts?.chatterbox || {};
    const install = chatterbox.install || {};
    const versionDisplay = runtime.version_display || 'unknown';
    const environmentLabel = runtime.is_container ? 'Docker image' : 'Local runtime';
    const chatterboxSummary = chatterbox.available
        ? 'Chatterbox available'
        : 'Chatterbox unavailable';
    const chatterboxDetail = chatterbox.available
        ? 'Chatterbox dependencies are available in the current runtime.'
        : (install.auto_install_error || 'Chatterbox dependencies are missing in the current runtime.');

    return `
        <div class="runtime-status-summary">
            <span class="runtime-chip runtime-chip-version">Version ${escapeHtml(versionDisplay)}</span>
            <span class="runtime-chip">${escapeHtml(environmentLabel)}</span>
            <span class="runtime-chip ${chatterbox.available ? 'runtime-chip-ok' : 'runtime-chip-warn'}">${escapeHtml(chatterboxSummary)}</span>
        </div>
        <div class="runtime-status-details">
            <span>Started: ${escapeHtml(formatStartTime(runtime.started_at_iso))}</span>
            <span> · ${escapeHtml(chatterboxDetail)}</span>
        </div>
    `;
}

export function renderRuntimeStatus(healthData = {}) {
    const panelEl = document.getElementById('runtimeStatusPanel');

    if (!panelEl) {
        return;
    }

    panelEl.innerHTML = buildRuntimeStatusMarkup(healthData);
}
