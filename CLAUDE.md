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
pyright app service utils

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
- `external_service/google_stt_api.py` — Google Cloud Speech-to-Text v2 wrapper; isolated here so it can be swapped without touching other layers
- `utils/` — `AppConfig` provides type-safe access to `utils/config.ini`; `env_loader` loads `.env` credentials

**Recording pipeline:**
1. Pause key → `RecordingLifecycle.toggle_recording()`
2. PyAudio captures PCM frames; `RecordingTimer` auto-stops at 60 s
3. On stop: `AudioFileManager` saves WAV, `google_stt_api.transcribe_pcm()` calls the API in a background thread
4. `text_transformer` applies punctuation rules and replacement dictionary (`data/replacements.txt`)
5. `ClipboardManager.copy_and_paste()` copies result then sends Ctrl+V via pynput's keyboard controller (`paste_backend.py`)
6. F8 key re-transcribes the last saved WAV without re-recording

**Key config:** `utils/config.ini` (audio, keys, Google STT model, paths, window)  
**Credentials:** `.env` with `GOOGLE_PROJECT_ID`, `GOOGLE_LOCATION`, `GOOGLE_CREDENTIALS_JSON`

## Coding Standards

- PEP8 + type hints on all functions
- Import order: stdlib → third-party → local (alphabetical within groups)
- Functions max 50 lines, single responsibility
- UI-facing strings in Japanese, centralized in constants
- Comments in Japanese, only when logic is non-obvious
