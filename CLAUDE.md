# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the application
python main.py

# Run tests
python -m pytest tests/ -v --tb=short

# Run tests with coverage
python -m pytest tests/ -v --tb=short --cov=app --cov-report=html

# Type check
pyright app external_service service utils

# Build executable
python build.py
```

Dependencies are managed with `uv`. After cloning: `uv sync`, then activate `.venv\Scripts\activate.bat`.

## Architecture

VoiceTrans is a Windows speech-to-text tool that captures voice via Pause key and pastes transcribed text into any active window using pynput's keyboard controller.

**Layer structure:**

- `main.py` → `Application` — initializes all components and runs `root.mainloop()`
- `app/` — Tkinter UI layer: `VoiceInputManager` orchestrates the UI; `UIQueueProcessor` handles thread-safe UI updates via a queue
- `service/` — Business logic: `RecordingLifecycle` owns the full pipeline (record → transcribe → paste); `AudioRecorder` wraps PyAudio; `TranscriptionHandler` coordinates API calls and text transforms; `ClipboardManager` handles copy+paste; `keyboard_handler` binds Pause/F8/F9/Esc
- `external_service/gemini_transcribe_api.py` — Gemini `gemini-3.5-transcribe` wrapper (`client.interactions.create`); isolated here so it can be swapped without touching other layers. `mode`/`language_codes`/`custom_vocabulary` are native `generation_config.transcription_config` parameters on this endpoint, so no prompt text is sent. `store=False` skips server-side retention. Known cost, re-measured on two real recordings (4.9 s and 12.2 s of speech, 3 warm runs each, medians): **2.0 s / 1.8 s** here vs **1.1 s / 1.3 s** for `generate_content` + `gemini-3.5-flash` — a **+0.5 to +0.9 s** regression, accepted in exchange for native transcription parameters. (An earlier 3.5–4.5 s figure for this endpoint did not reproduce; it appears to have been measured on non-speech or unwarmed connections. Cold start adds only ~0.6 s.) `service_tier='priority'` was measured and **rejected**: no latency gain (medians 1.89 s / 2.31 s, i.e. at or slightly above standard) for a 75–100% per-token premium. Note the model's rate limit is **10 requests/min** — rapid successive dictations can hit HTTP 429
- `utils/` — `AppConfig` provides type-safe access to `utils/config.ini`; `env_loader` loads `.env` credentials

**Recording pipeline:**
1. Pause key → `RecordingLifecycle.toggle_recording()`
2. PyAudio captures PCM frames; `RecordingTimer` auto-stops at 60 s
3. On stop: `gemini_transcribe_api.transcribe_pcm()` calls the API in a background thread while `AudioFileManager` saves the WAV in a parallel thread (archive only — it must not delay the request). PCM is wrapped in an in-memory WAV container and sent inline as base64 — inline `audio/wav` carries sample rate and channels in its header and avoids the Files API round trip the docs' example uses
4. `text_transformer` applies punctuation rules and replacement dictionary (`data/replacements.txt`)
5. `ClipboardManager.copy_and_paste()` copies result then sends Ctrl+V via pynput's keyboard controller (`paste_backend.py`)
6. F8 key re-transcribes the last saved WAV without re-recording

**Key config:** `utils/config.ini` (audio, keys, `[GEMINI]` model/language_codes/mode/custom_vocabulary_file, paths, window). `mode` is `verbatim` or `smart`; `smart` lets the model restructure text, which interferes with the F9 punctuation toggle and `replacements.txt`. Note `save_config()` rewrites config.ini via `ConfigParser.write()` on every F9 press, which strips comments — so don't put comments there.  
**Credentials:** `.env` with `GEMINI_API_KEY`

## Coding Standards

- PEP8 + type hints on all functions
- Import order: stdlib → third-party → local (alphabetical within groups)
- Functions max 50 lines, single responsibility
- UI-facing strings in Japanese, centralized in constants
- Comments in Japanese, only when logic is non-obvious
