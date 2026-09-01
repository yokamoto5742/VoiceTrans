# CLAUDE.md

このファイルは、Claude Code (claude.ai/code) がこのリポジトリのコードを扱う際のガイダンスを提供します。

## コマンド

```bash
# アプリケーションの実行
python main.py

# テストの実行
python -m pytest tests/ -v --tb=short

# カバレッジ付きテストの実行
python -m pytest tests/ -v --tb=short --cov=app --cov-report=html

# 型チェック
pyright app external_service service utils

# 実行ファイルのビルド
python build.py
```

依存関係は `uv` で管理します。クローン後は `uv sync` を実行し、`.venv\Scripts\activate.bat` を有効化します。

## アーキテクチャ

VoiceTrans は Windows 向けの音声文字起こしツールです。Pause キーで音声を取り込み、pynput のキーボードコントローラーを使って文字起こし結果を任意のアクティブウィンドウに貼り付けます。

**レイヤー構造:**

- `main.py` → `Application` — すべてのコンポーネントを初期化し、`root.mainloop()` を実行する
- `app/` — Tkinter の UI レイヤー: `VoiceInputManager` が UI を統括し、`UIQueueProcessor` がキューを介してスレッドセーフな UI 更新を処理する
- `service/` — ビジネスロジック: `RecordingLifecycle` がパイプライン全体（録音 → 文字起こし → 貼り付け）を保持する。`AudioRecorder` は PyAudio をラップする。`TranscriptionHandler` は API 呼び出しとテキスト変換を調整する。`ClipboardManager` はコピー＋貼り付けを処理する。`keyboard_handler` は Pause/F8/F9/Esc をバインドする
- `external_service/gemini_transcribe_api.py` — Gemini `gemini-3.5-transcribe` のラッパー（`client.interactions.create`）。他のレイヤーに触れずに差し替えられるよう、ここに分離している。`mode`/`language_codes`/`custom_vocabulary` はこのエンドポイントでは `generation_config.transcription_config` のネイティブパラメータであり、プロンプトテキストは送信されない。`store=False` によりサーバー側での保持をスキップする。`service_tier='priority'` は計測のうえ**却下**した。なお、このモデルのレート制限は **10 リクエスト/分** — 立て続けの口述で HTTP 429 に達することがある
- `utils/` — `AppConfig` は `utils/config.ini` への型安全なアクセスを提供する。`env_loader` は `.env` の認証情報を読み込む

**録音パイプライン:**
1. Pause キー → `RecordingLifecycle.toggle_recording()`
2. PyAudio が PCM フレームを取り込む。`RecordingTimer` が 60 秒で自動停止する
3. 停止時: `gemini_transcribe_api.transcribe_pcm()` がバックグラウンドスレッドで API を呼び出し、それと並行して `AudioFileManager` が別スレッドで WAV を保存する（アーカイブ専用であり、リクエストを遅延させてはならない）。PCM はメモリ上の WAV コンテナにラップされ、base64 でインライン送信される — インラインの `audio/wav` はヘッダーにサンプルレートとチャンネル数を持ち、ドキュメントの例が用いる Files API の往復を回避できる
4. `text_transformer` が句読点ルールと置換辞書（`data/replacements.txt`）を適用する
5. `ClipboardManager.copy_and_paste()` が結果をコピーし、pynput のキーボードコントローラー（`paste_backend.py`）で Ctrl+V を送信する
6. F8 キーは再録音せずに、最後に保存された WAV を再度文字起こしする

**主な設定:** `utils/config.ini`（audio、keys、`[GEMINI]` の model/language_codes/mode/custom_vocabulary_file、paths、window）。`mode` は `verbatim` または `smart`。`smart` はモデルによるテキストの再構成を許可するため、F9 の句読点トグルや `replacements.txt` と干渉する。
**認証情報:** `GEMINI_API_KEY` を含む `.env`

## コーディング規約・作業ルール

詳細は `.claude/rules/` の各ファイルを参照し、必ず従うこと。

- `.claude/rules/python-coding.md` — PEP8、型ヒント必須、import 順、クリーンコード、コメント、UI メッセージ
- `.claude/rules/coding-guidelines.md` — 実装前に考える／シンプルさ最優先／外科的な変更／目標駆動の実行
- `.claude/rules/response-style.md` — パッチ差分で返す、変更範囲は最小限、修正は直接適用
- `.claude/rules/testing.md` — テスト実行コマンド（`.venv\Scripts\python.exe -m pytest`）
- `.claude/rules/commit.md` — コミットメッセージのプレフィックスと記述ルール
- `.claude/rules/database.md` — マイグレーション操作（該当ファイルを扱う場合のみ）
