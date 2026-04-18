# Chatterbox TTS exposure design

## Problem

Chatterbox TTS already exists in the codebase as a backend provider, API surface, config model, and partial frontend support. It is not fully exposed to end users because the main translation UI does not render the expected TTS controls, the translation form does not submit the provider-specific fields, and the CLI does not expose a provider switch.

## Scope

This design covers only the missing user-facing integration points needed to make Chatterbox selectable and usable.

In scope:
- expose TTS provider selection in the main web translation interface
- expose Chatterbox-specific controls already supported by the backend
- submit the selected TTS provider and Chatterbox options with translation requests
- add a CLI `--tts-provider` option and validate Chatterbox availability before use
- document the new CLI option and the practical Chatterbox constraints

Out of scope:
- rewriting the Chatterbox provider implementation
- adding Docker GPU images or containerized CUDA support
- changing the TTS generation backend contract
- adding a full Chatterbox installer flow

## Approaches considered

### 1. Minimal exposure only

Wire only the missing web template controls and keep CLI unchanged.

Pros:
- smallest diff
- lowest implementation risk

Cons:
- CLI remains inconsistent with backend capabilities
- users still cannot select Chatterbox cleanly outside the web UI

### 2. Full user-surface completion (**recommended**)

Complete the missing web UI, form submission, and CLI provider switch while reusing the existing backend/API/TTS manager.

Pros:
- uses existing code instead of re-implementing
- aligns backend, web UI, and CLI
- keeps changes focused on the real gaps

Cons:
- touches a few integration files instead of one

### 3. New TTS settings architecture

Refactor TTS UI, config persistence, and provider handling into a larger dedicated subsystem.

Pros:
- could improve long-term structure

Cons:
- unnecessary for the current need
- higher regression risk
- violates YAGNI

## Selected design

Use approach 2.

The implementation will treat Chatterbox as an already-supported provider and finish the missing exposure layer.

## Architecture

### Web UI

Add a TTS settings block to `src/web/templates/translation_interface.html` that provides:
- TTS enable toggle
- provider selector (`edge-tts`, `chatterbox`)
- generic audio controls already expected by the frontend
- Chatterbox-only controls:
  - voice prompt selector
  - voice prompt upload input
  - exaggeration slider
  - cfg weight slider
  - GPU status panel

The HTML IDs must match the existing expectations in `src/web/static/js/tts/tts-manager.js`.

### Form submission

Extend `src/web/static/js/ui/form-manager.js` so the translation payload includes:
- `tts_provider`
- `tts_voice_prompt_path`
- `tts_exaggeration`
- `tts_cfg_weight`

These fields should only be populated when TTS is enabled, with safe defaults matching current backend expectations.

### CLI

Add `--tts-provider` to `translate.py` with choices `edge-tts` and `chatterbox`.

Before TTS generation starts, if the selected provider is `chatterbox`, validate availability with the existing backend/provider helper and fail with a clear actionable message if dependencies are missing.

### Backend

No contract change is required unless implementation reveals a concrete mismatch. The existing API and provider code remain the source of truth.

## Data flow

### Web path

1. User enables TTS in the translation UI.
2. User selects provider.
3. If provider is `chatterbox`, the existing `tts-manager.js` logic shows Chatterbox-only controls and fetches provider/GPU/voice-prompt data from existing API routes.
4. `form-manager.js` includes the selected TTS settings in the translation request.
5. Backend translation/TTS flow uses `TTSConfig.from_web_request()` and existing provider creation logic.

### CLI path

1. User passes `--tts --tts-provider chatterbox`.
2. CLI builds `TTSConfig` with the selected provider.
3. CLI validates provider availability before generation.
4. Existing TTS pipeline runs unchanged.

## Error handling

- If Chatterbox is unavailable, web UI should keep the option disabled or visibly unavailable using the already-existing TTS manager behavior.
- If the user selects Chatterbox through CLI without dependencies installed, fail early with a clear message listing missing dependencies.
- If GPU is unavailable, surface backend status as informational. Do not block CPU fallback unless current provider code already does.
- Do not introduce silent fallback from `chatterbox` to `edge-tts`. Respect explicit provider choice.

## Testing

Add or update tests to cover:
- CLI argument parsing for `--tts-provider`
- web payload construction including `tts_provider` and Chatterbox-specific fields
- template presence of the expected TTS element IDs
- any lightweight backend validation path touched by the CLI change

Prefer targeted tests over broad refactoring.

## Risks

- The codebase appears to contain partially integrated TTS UI logic. The main risk is wiring duplicate or conflicting TTS control paths.
- The translation interface template may need small styling support for the new controls.
- Chatterbox dependency availability differs across environments; tests must avoid requiring actual GPU or model downloads.

## Success criteria

- Chatterbox appears as a selectable TTS provider in the main web translation interface.
- Translation requests sent from the web UI include the provider-specific TTS fields.
- CLI users can select Chatterbox with `--tts-provider`.
- Explicit Chatterbox selection fails clearly when dependencies are unavailable.
- Existing Edge-TTS behavior remains unchanged.
