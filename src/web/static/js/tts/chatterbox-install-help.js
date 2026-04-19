function escapeHtml(value) {
    return String(value ?? '')
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#39;');
}

export function buildChatterboxInstallHelp(providerInfo = {}) {
    if (!providerInfo || providerInfo.available) {
        return '';
    }

    const install = providerInfo.install || providerInfo;
    const installCommand = install.install_command || '';
    const installError = install.auto_install_error || '';
    const copyLabel = install.install_method === 'docker-build'
        ? 'Copy Docker rebuild command'
        : 'Copy install command';
    const heading = install.is_container
        ? 'Chatterbox is not installed in this Docker image.'
        : 'Chatterbox is not installed in this Python environment.';
    const missing = Array.isArray(install.missing_dependencies) && install.missing_dependencies.length > 0
        ? `<p style="margin: 8px 0 0 0; font-size: 0.8rem; color: var(--text-secondary);">Missing: ${escapeHtml(install.missing_dependencies.join(', '))}</p>`
        : '';
    const installCommandBlock = installCommand
        ? `
            <p style="margin: 12px 0 6px 0; font-size: 0.8rem; color: var(--text-secondary);">Recommended command:</p>
            <code id="chatterboxInstallCommand" style="display: block; margin-top: 6px; padding: 8px; background: rgba(15, 23, 42, 0.55); border-radius: 6px; color: var(--text-primary); white-space: pre-wrap;">${escapeHtml(installCommand)}</code>
            <button type="button" id="copyChatterboxInstallCommand" class="btn btn-secondary" style="margin-top: 10px;">
                ${copyLabel}
            </button>
        `
        : '';

    return `
        <div id="ttsModalChatterboxInstallHelp" style="margin-top: 16px; padding: 12px; border-radius: 8px; border: 1px solid #ef4444; background: rgba(127, 29, 29, 0.12);">
            <p style="margin: 0; color: #fca5a5; font-size: 0.9rem; font-weight: 600;">${heading}</p>
            <p style="margin: 8px 0 0 0; font-size: 0.85rem; color: var(--text-secondary);">${escapeHtml(installError)}</p>
            ${missing}
            ${installCommandBlock}
        </div>
    `;
}
