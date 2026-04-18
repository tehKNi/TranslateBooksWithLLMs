# Chatterbox TTS Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Chatterbox selectable and usable from the main web translation UI and the CLI without changing the existing backend provider contract.

**Architecture:** Reuse the Chatterbox backend, API routes, and `TTSManager` that already exist. Fill only the missing integration points: render the expected TTS controls in the main template, submit provider-specific TTS fields from the translation form, and expose a CLI `--tts-provider` switch with explicit availability validation.

**Tech Stack:** Python 3, Flask/Jinja template, vanilla ES modules, pytest, Node built-in test runner

---

## File structure map

- Create: `tests/web/tts-request-config.test.mjs` — Node-level tests for a pure TTS payload builder with no browser dependency
- Create: `tests/unit/test_translation_interface_tts_template.py` — pytest coverage for the main template TTS control IDs
- Create: `tests/unit/test_translate_tts_provider.py` — pytest coverage for CLI parser + Chatterbox validation
- Create: `src/web/static/js/tts/tts-request-config.js` — pure helper that builds translation-request TTS payloads
- Modify: `.gitignore` — add the narrowest exceptions required so newly added tests under `tests/` are tracked on this branch
- Modify: `src/web/static/js/translation/batch-controller.js` — use the pure TTS payload builder in the real translation request flow
- Modify: `src/web/static/js/ui/form-manager.js` — reuse the same helper so validation/config views stay aligned
- Modify: `src/web/templates/translation_interface.html` — add the missing TTS provider and Chatterbox controls expected by `TTSManager`
- Modify: `translate.py` — extract parser/validation helpers and add `--tts-provider`
- Modify: `docs/CLI.md` — document the new CLI/provider behavior in the canonical CLI reference

### Task 1: Build and test the web TTS payload helper

**Files:**
- Create: `src/web/static/js/tts/tts-request-config.js`
- Modify: `src/web/static/js/translation/batch-controller.js`
- Modify: `src/web/static/js/ui/form-manager.js`
- Test: `tests/web/tts-request-config.test.mjs`

- [ ] **Step 1: Write the failing Node tests**

```javascript
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
```

- [ ] **Step 2: Run the Node test to verify it fails**

Run: `node --test /workspace/projects/TranslateBooksWithLLMs/tests/web/tts-request-config.test.mjs`
Expected: FAIL with `Cannot find module` or `buildTTSRequestConfig is not exported`

- [ ] **Step 3: Write the minimal helper implementation**

```javascript
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
        config.tts_exaggeration = Number.parseFloat(exaggeration || '0.5');
        config.tts_cfg_weight = Number.parseFloat(cfgWeight || '0.5');
    }

    return config;
}
```

- [ ] **Step 4: Wire the helper into the real request builders**

```javascript
import { buildTTSRequestConfig } from '../tts/tts-request-config.js';

const ttsConfig = buildTTSRequestConfig({
    ttsEnabled: DomHelpers.getElement('ttsEnabled')?.checked || false,
    ttsProvider: DomHelpers.getValue('ttsProvider') || 'edge-tts',
    ttsVoice: DomHelpers.getValue('ttsVoice') || '',
    ttsRate: DomHelpers.getValue('ttsRate') || '+0%',
    ttsFormat: DomHelpers.getValue('ttsFormat') || 'opus',
    ttsBitrate: DomHelpers.getValue('ttsBitrate') || '64k',
    voicePromptPath: DomHelpers.getValue('voicePromptSelect') || '',
    exaggeration: DomHelpers.getValue('ttsExaggeration') || '0.5',
    cfgWeight: DomHelpers.getValue('ttsCfgWeight') || '0.5'
});

return {
    // existing translation fields...
    ...ttsConfig
};
```

Apply the same spread pattern in:

```javascript
// src/web/static/js/translation/batch-controller.js
const config = {
    source_language: sourceLanguageVal,
    target_language: targetLanguageVal,
    // existing fields...
    bilingual_output: DomHelpers.getElement('bilingualMode')?.checked || false,
    ...buildTTSRequestConfig({
        ttsEnabled: DomHelpers.getElement('ttsEnabled')?.checked || false,
        ttsProvider: DomHelpers.getValue('ttsProvider') || 'edge-tts',
        ttsVoice: DomHelpers.getValue('ttsVoice') || '',
        ttsRate: DomHelpers.getValue('ttsRate') || '+0%',
        ttsFormat: DomHelpers.getValue('ttsFormat') || 'opus',
        ttsBitrate: DomHelpers.getValue('ttsBitrate') || '64k',
        voicePromptPath: DomHelpers.getValue('voicePromptSelect') || '',
        exaggeration: DomHelpers.getValue('ttsExaggeration') || '0.5',
        cfgWeight: DomHelpers.getValue('ttsCfgWeight') || '0.5'
    })
};
```

- [ ] **Step 5: Run the focused checks**

Run:
```bash
node --test /workspace/projects/TranslateBooksWithLLMs/tests/web/tts-request-config.test.mjs
node --check /workspace/projects/TranslateBooksWithLLMs/src/web/static/js/translation/batch-controller.js
node --check /workspace/projects/TranslateBooksWithLLMs/src/web/static/js/ui/form-manager.js
node --check /workspace/projects/TranslateBooksWithLLMs/src/web/static/js/tts/tts-request-config.js
```

Expected: all commands PASS

- [ ] **Step 6: Commit**

```bash
git add tests/web/tts-request-config.test.mjs \
        src/web/static/js/tts/tts-request-config.js \
        src/web/static/js/translation/batch-controller.js \
        src/web/static/js/ui/form-manager.js
git commit -m "feat: wire chatterbox tts request payload" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 2: Render the missing TTS controls in the main translation template

**Files:**
- Modify: `.gitignore` (only if needed to track the new test file on this branch)
- Modify: `src/web/templates/translation_interface.html`
- Test: `tests/unit/test_translation_interface_tts_template.py`

- [ ] **Step 1: Write the failing template test**

```python
from pathlib import Path


def test_translation_interface_exposes_chatterbox_tts_controls():
    template = Path("src/web/templates/translation_interface.html").read_text(encoding="utf-8")

    required_ids = [
        'ttsEnabled',
        'ttsOptions',
        'ttsProvider',
        'edgeTTSOptions',
        'chatterboxOptions',
        'gpuStatusSection',
        'ttsVoice',
        'ttsVoiceHelp',
        'ttsRate',
        'ttsFormat',
        'ttsBitrate',
        'voicePromptSelect',
        'voicePromptInput',
        'uploadVoicePromptBtn',
        'voicePromptUploadStatus',
        'ttsExaggeration',
        'exaggerationValue',
        'ttsCfgWeight',
        'cfgWeightValue',
        'gpuStatusIndicator',
        'gpuName',
        'gpuVram',
        'gpuStatusDot',
    ]

    for element_id in required_ids:
        assert f'id="{element_id}"' in template
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspace/projects/TranslateBooksWithLLMs && python3 -m pytest tests/unit/test_translation_interface_tts_template.py -v`
Expected: FAIL because the required TTS IDs are missing from the template

- [ ] **Step 3: Add the missing template block with the IDs already used by `TTSManager`**

```html
<div class="form-group" style="margin-bottom: 15px;">
    <label style="display: flex; align-items: flex-start; gap: 10px; cursor: pointer;">
        <input type="checkbox" id="ttsEnabled">
        <div>
            <span style="font-weight: 600; color: var(--text-dark);">Generate TTS Audio</span>
        </div>
    </label>
</div>

<div id="ttsOptions" style="display: none;">
    <div class="form-group">
        <label for="ttsProvider">TTS Provider</label>
        <div class="neu-inset-light">
            <select class="form-control" id="ttsProvider">
                <option value="edge-tts">Edge-TTS</option>
                <option value="chatterbox">Chatterbox TTS</option>
            </select>
        </div>
    </div>

    <div id="edgeTTSOptions">
        <div class="form-group">
            <label for="ttsVoice">Voice (auto-select if empty)</label>
            <div class="neu-inset-light">
                <input type="text" class="form-control" id="ttsVoice" placeholder="e.g., zh-CN-XiaoxiaoNeural">
            </div>
            <small id="ttsVoiceHelp">Leave empty for auto-selection based on target language</small>
        </div>
        <div class="form-group">
            <label for="ttsRate">Speech Rate</label>
            <div class="neu-inset-light">
                <input type="text" class="form-control" id="ttsRate" value="+0%">
            </div>
        </div>
    </div>

    <div id="chatterboxOptions" style="display: none;">
        <div class="form-group">
            <label for="voicePromptSelect">Voice Prompt</label>
            <div class="neu-inset-light">
                <select class="form-control" id="voicePromptSelect">
                    <option value="">Select a voice prompt</option>
                </select>
            </div>
        </div>
        <div class="form-group">
            <label for="voicePromptInput">Upload Voice Prompt</label>
            <input type="file" id="voicePromptInput" accept=".wav,.mp3,.flac,.m4a,.ogg">
            <button type="button" id="uploadVoicePromptBtn" class="btn btn-secondary">Upload</button>
            <small id="voicePromptUploadStatus"></small>
        </div>
        <div class="form-group">
            <label for="ttsExaggeration">Exaggeration <span id="exaggerationValue">0.50</span></label>
            <input type="range" id="ttsExaggeration" min="0" max="1" step="0.05" value="0.5">
        </div>
        <div class="form-group">
            <label for="ttsCfgWeight">CFG Weight <span id="cfgWeightValue">0.50</span></label>
            <input type="range" id="ttsCfgWeight" min="0" max="1" step="0.05" value="0.5">
        </div>
    </div>

    <div id="gpuStatusSection" style="display: none;">
        <div id="gpuStatusIndicator" class="gpu-status gpu-unavailable">
            <span id="gpuStatusDot" class="status-dot unavailable"></span>
            <span id="gpuName">CPU Mode (No CUDA)</span>
            <span id="gpuVram">N/A</span>
        </div>
    </div>

    <div class="form-group">
        <label for="ttsFormat">Audio Format</label>
        <div class="neu-inset-light">
            <select class="form-control" id="ttsFormat">
                <option value="opus">opus</option>
                <option value="mp3">mp3</option>
            </select>
        </div>
    </div>
    <div class="form-group">
        <label for="ttsBitrate">Bitrate</label>
        <div class="neu-inset-light">
            <input type="text" class="form-control" id="ttsBitrate" value="64k">
        </div>
    </div>
</div>
```

- [ ] **Step 4: Run the focused checks**

Run:
```bash
cd /workspace/projects/TranslateBooksWithLLMs && python3 -m pytest tests/unit/test_translation_interface_tts_template.py -v
node --check /workspace/projects/TranslateBooksWithLLMs/src/web/static/js/tts/tts-manager.js
```

Expected: pytest PASS, JS syntax check PASS

- [ ] **Step 5: Commit**

```bash
git add tests/unit/test_translation_interface_tts_template.py \
        src/web/templates/translation_interface.html
git commit -m "feat: expose chatterbox controls in web ui" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 3: Add CLI provider selection and explicit Chatterbox validation

**Files:**
- Modify: `translate.py`
- Modify: `docs/CLI.md`
- Test: `tests/unit/test_translate_tts_provider.py`

- [ ] **Step 1: Write the failing CLI tests**

```python
import pytest

import translate


def test_build_parser_accepts_tts_provider_choice():
    parser = translate.build_parser()

    args = parser.parse_args([
        "--input", "book.txt",
        "--tts",
        "--tts-provider", "chatterbox",
    ])

    assert args.tts_provider == "chatterbox"


def test_validate_tts_provider_rejects_missing_chatterbox_dependencies(monkeypatch):
    parser = translate.build_parser()
    args = parser.parse_args([
        "--input", "book.txt",
        "--tts",
        "--tts-provider", "chatterbox",
    ])

    monkeypatch.setattr(translate, "is_chatterbox_available", lambda: False)

    with pytest.raises(SystemExit):
        translate.validate_cli_args(parser, args)
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /workspace/projects/TranslateBooksWithLLMs && python3 -m pytest tests/unit/test_translate_tts_provider.py -v`
Expected: FAIL because `build_parser` and `validate_cli_args` do not exist yet

- [ ] **Step 3: Extract parser + validation helpers and add `--tts-provider`**

```python
from src.tts.providers import is_chatterbox_available


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Translate a text, EPUB or SRT file using an LLM.")
    # existing arguments...
    tts_group = parser.add_argument_group('TTS Options', 'Text-to-Speech audio generation')
    tts_group.add_argument("--tts", action="store_true", default=TTS_ENABLED, help="Generate audio from translated text.")
    tts_group.add_argument("--tts-provider", default=TTS_PROVIDER, choices=["edge-tts", "chatterbox"], help="TTS provider.")
    return parser


def validate_cli_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.tts and args.tts_provider == "chatterbox" and not is_chatterbox_available():
        parser.error("--tts-provider chatterbox requires chatterbox-tts, torch, and torchaudio to be installed")
```

- [ ] **Step 4: Pass the selected provider into the existing TTS config flow**

```python
def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    validate_cli_args(parser, args)
    # existing translation flow...
    tts_config = TTSConfig.from_cli_args(args)
```

Also document the option in `docs/CLI.md` with a small example:

```markdown
### Chatterbox TTS

Use Chatterbox explicitly from the CLI:

~~~bash
python3 translate.py --input book.txt --tts --tts-provider chatterbox
~~~

Requires local Chatterbox dependencies such as `chatterbox-tts`, `torch`, and `torchaudio`.
```

- [ ] **Step 5: Run the focused checks**

Run:
```bash
cd /workspace/projects/TranslateBooksWithLLMs && python3 -m pytest tests/unit/test_translate_tts_provider.py -v
python3 -m py_compile /workspace/projects/TranslateBooksWithLLMs/translate.py
```

Expected: pytest PASS, Python compile PASS

- [ ] **Step 6: Commit**

```bash
git add tests/unit/test_translate_tts_provider.py \
        translate.py \
        docs/CLI.md
git commit -m "feat: add chatterbox cli provider selection" \
  -m "Co-authored-by: Copilot <223556219+Copilot@users.noreply.github.com>"
```

### Task 4: Final integration verification

**Files:**
- Reuse modified files from Tasks 1-3

- [ ] **Step 1: Run the focused automated checks together**

Run:
```bash
cd /workspace/projects/TranslateBooksWithLLMs && \
python3 -m pytest tests/unit/test_translation_interface_tts_template.py tests/unit/test_translate_tts_provider.py -v && \
node --test tests/web/tts-request-config.test.mjs && \
node --check src/web/static/js/translation/batch-controller.js && \
node --check src/web/static/js/ui/form-manager.js && \
node --check src/web/static/js/tts/tts-manager.js && \
node --check src/web/static/js/tts/tts-request-config.js && \
python3 -m py_compile translate.py
```

Expected: all focused checks PASS

- [ ] **Step 2: Run the existing targeted regression already added in this session**

Run: `cd /workspace/projects/TranslateBooksWithLLMs && python3 -m pytest tests/unit/test_ffmpeg_installation.py -v`
Expected: PASS

- [ ] **Step 3: Review the diff for unintended scope**

Run:
```bash
cd /workspace/projects/TranslateBooksWithLLMs && git --no-pager diff -- \
    src/web/templates/translation_interface.html \
    src/web/static/js/translation/batch-controller.js \
    src/web/static/js/ui/form-manager.js \
    src/web/static/js/tts/tts-request-config.js \
    translate.py \
    docs/CLI.md \
    tests/unit/test_translation_interface_tts_template.py \
    tests/unit/test_translate_tts_provider.py \
    tests/web/tts-request-config.test.mjs
```

Expected: only Chatterbox exposure, CLI selection, and associated tests/docs changes appear

- [ ] **Step 4: Stop if the focused checks or diff review show extra scope**

No new code belongs in this step. If the diff shows unrelated files or if any focused check failed, go back to the task that introduced the issue instead of adding more changes here.

## Self-review

- Spec coverage:
  - web provider exposure -> Task 2
  - web request payload -> Task 1
  - CLI provider switch + validation -> Task 3
  - docs update -> Task 3
  - focused verification -> Task 4
- Placeholder scan: no `TODO`, `TBD`, or implicit "test this later" steps remain
- Type consistency:
  - web payload field names match backend contract: `tts_provider`, `tts_voice_prompt_path`, `tts_exaggeration`, `tts_cfg_weight`
  - CLI helper names are consistent: `build_parser`, `validate_cli_args`
