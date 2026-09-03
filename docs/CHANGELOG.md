# 変更履歴

このプロジェクトのすべての重要な変更は、このファイルに記録されます。

フォーマットは [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に基づいており、
バージョン番号は [Semantic Versioning](https://semver.org/lang/ja/) に従っています。

## [Unreleased]

## [1.0.2] - 2026-09-03

### 追加
- 置換辞書の動的再読み込み機能を実装（起動中に編集内容を即座に反映、再起動不要）
- 置換辞書編集時のコールバック機能を追加し、UI更新を自動化
- テキスト整形パイプラインを統一し、処理順序を明確化（空白除去→置換→句読点処理）

### 変更
- テキスト置換処理を ClipboardManager から TranscriptionHandler に移動し、アーキテクチャを改善
- 置換辞書と句読点処理を TranscriptionHandler に統合し、テキスト整形の一元管理を実現
- Application クラスから ClipboardManager への置換辞書引数を削除

## [1.0.1] - 2026-09-02

### 追加
- 文字起こしモード（verbatim/smart）の正規化とバリデーション機能を実装
- デフォルト値の定数化（`DEFAULT_GEMINI_MODE`, `DEFAULT_GEMINI_MODEL`）で設定の一元管理を強化
- 設定ファイル読み込みのテストケースを追加

### 変更
- `env_loader.py`: config.ini のパス取得を `get_config_path()` 関数を使用するように変更
- `text_transformer.py`: 日本語空白処理関数を `remove_ja_en_spaces()` から `remove_ja_spaces()` にリネーム・改善し、連続する空白の処理を最適化
- `app_config.py`: gemini_mode のセッターにバリデーション処理を追加し、無効な設定値の検出・拒否を強化

## [1.0.0] - 2026-08-31
- 初版リリース
