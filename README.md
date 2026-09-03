# VoiceTrans

**専門用語を登録できるWindows 用ショートカット型音声入力ツール**

Pause キー で録音開始/終了 、文字起こし結果をアクティブウィンドウへ直接貼り付け。1 日 100 回以上の短文作成が可能な設計です。

---

## 目次

- [VoiceTrans 開発の経緯](#VoiceTrans-開発の経緯)
- [想定ユーザーと使用シーン](#想定ユーザーと使用シーン)
- [特徴](#特徴)
- [専門用語登録機能](#専門用語登録機能)
- [置換ルールのサンプル](#置換ルールのサンプル)
- [クイックスタート](#クイックスタート)
- [使い方](#使い方)
- [設計のポイント](#設計のポイント)
- [設定](#設定)
- [開発者向け情報](#開発者向け情報)
  - [テスト](#テスト)
  - [型チェック](#型チェック)
  - [実行ファイルのビルド](#実行ファイルのビルド)
- [システム要件](#システム要件)
- [使用料金について](#使用料金について)
- [トラブルシューティング](#トラブルシューティング)
- [ライセンス](#ライセンス)
- [更新履歴](#更新履歴)
- [免責事項](#免責事項)

---

## VoiceTrans 開発の経緯

既存の音声入力アプリには、以下のような不都合がありました。

- ❌ **Windows 標準の音声入力は日本語の認識精度が弱い**
- ❌ **ファイル名の変更欄などに貼り付けられない**
- ❌ **他のクラウド型アプリではネット瞬断時に音声が消失して再発声が必要**

VoiceTrans はこれらを次の組み合わせで解決します。

- **Gemini 3.5 Transcribe** による高い日本語認識精度
- **Win32 SendInput** による貼り付け先非依存の入力
- **ローカル WAV 保存** による通信瞬断への耐性（F8 キーで再送可能）

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 想定ユーザーと使用シーン

パソコンで事務作業を行う方が、以下の用途で使うことを想定しています。

- 業務メール文章の作成
- ファイル名、チャット欄などへの直接入力
- 生成 AI へのプロンプト入力
- 議事録の作成

**想定ワークフロー:** 1 日 100 回以上 × 1 回 60 秒以下の **短文作成** 型。長時間音声の文字起こしではなく、思いついたときにショートカットキーで素早く短文を入力する用途に最適です。

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 特徴

1. **ショートカットで録音** — Pause キーで録音開始/終了(録音中は画面右下のツールバーにマイクマークが出ます)
2. **貼り付け先を選ばない** — ファイル名やダイアログ等にも入力可能
3. **ネット瞬断に強い** — 音声はローカルに WAV ファイルで一時保存されるため通信失敗時も F8 キーで再送可能
4. **専門用語登録機能** — 専門用語を登録して認識精度を向上
5. **置換ルールによる後処理置換** — `data/replacements.txt` に登録して誤認識を修正

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

## 専門用語登録機能

`data/technical_terms.txt` に専門用語を登録すると、Gemini API へカスタム語彙として送信され、認識精度が向上します。

### 登録方法

`data/technical_terms.txt` に 1 行 1 フレーズで登録します。

```
加齢黄斑変性
硝子体注射
```

医療用語や業界用語など、一般的でない固有の専門用語のみを登録してください。日常語を登録すると逆効果になります。登録は最大 1000 語ですが、100 語程度までが最も効果的です。

### 実装動作

アプリケーション起動時に `data/technical_terms.txt` を読み込み、Gemini API へ `custom_vocabulary` として設定されます。これにより以下のような効果が期待できます。

- 医療系の専門用語（「加齢黄斑変性」など）の誤認識を削減
- 部署名や業務用語の正確な認識

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 置換ルールのサンプル

`data/replacements.txt` に CSV 形式で登録します。アプリ画面の「置換辞書登録」ボタンから編集でき、保存すると再起動なしで次回の文字起こしから反映されます。実際の運用例を抜粋します。

```csv
# 医療系の同音異義語を補正
小児体,硝子体

# 不要な疑問符を句点に
?,。
```

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## クイックスタート

### 1. リポジトリをクローン

```bash
git clone https://github.com/your-repo/VoiceTrans.git
cd VoiceTrans
```

### 2. 仮想環境の作成と依存パッケージのインストール

事前に [uv](https://docs.astral.sh/uv/getting-started/installation/) のインストールが必要です。

```bash
# 仮想環境の作成とパッケージのインストールを一度に行う
uv sync
```

仮想環境を有効化する：

```bash
# Windows (Command Prompt)
.venv\Scripts\activate.bat

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Mac / Linux
source .venv/bin/activate
```

### 3. Gemini API キーを設定

#### 3-1. API キーを取得

[Google AI Studio](https://aistudio.google.com/apikey) で API キーを発行します。

#### 3-2. .env ファイルを作成

```
GEMINI_API_KEY=AIza...
```

`.env` は初回起動時に `%APPDATA%\VoiceTrans\.env` へコピーされ、以降はそちらが優先して読み込まれます。既存ユーザーがバージョンアップする場合は、`%APPDATA%\VoiceTrans\.env` を直接書き換えてください。

### 4. 起動

```bash
python main.py
```

起動後、Pause キーを押して録音 → 話す → Pause キーで停止すると、アクティブウィンドウへテキストが貼り付けられます。

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 使い方

### キーボードショートカット

| キー | 機能                          |
|------|-----------------------------|
| Pause | 録音開始 / 停止                   |
| Esc | アプリケーション終了                  |
| **F8** | **直前の音声を再変換（ネット瞬断時の再送に使用）** |
| F9 | 句読点機能の有効 / 無効を切り替え          |

### 基本フロー

1. Pause キーを押して録音開始
2. マイクに向かって話す（デフォルトは最大 60 秒で自動停止）
3. Pause キーで停止(無発声で自動終了)
4. テキストが自動的にアクティブウィンドウへ貼り付けられる

ネット切断などで変換に失敗した場合は、**F8 キーで直前の音声を再送信** できます。音声データはローカルに保存されているため、発声し直す必要がありません。

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 設計のポイント

### レイヤー構成

- **`app/`** — Tkinter UI レイヤー。`VoiceInputManager` がメインウィンドウを保持。全 UI 更新は `UIQueueProcessor` 経由
- **`service/`** — ビジネスロジック。`RecordingLifecycle` が `AudioRecorder` → `AudioFileManager` → `TranscriptionHandler` → `TextTransformer` → `ClipboardManager` → `paste_backend` のパイプラインを統合
- **`external_service/`** — Gemini API の薄いラッパー
- **`utils/`** — 設定 (`AppConfig`)、ロギング、クラッシュログ、シグナル設定

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 設定

### 主要な設定 (utils/config.ini)

| セクション | 用途 |
|-----------|------|
| `[GEMINI]` | モデル (`gemini-3.5-transcribe`)、言語 (`ja-JP`)、文字起こしモード、カスタム語彙ファイル |
| `[KEYS]` | ショートカット割り当て (Pause: 録音、F8: 再変換、F9: 句読点切替、Esc: 終了) |
| `[RECORDING]` | 自動停止タイマー（デフォルト 60 秒） |
| `[PATHS]` | 置換ルールファイル、一時ファイル保存先 |

### 文字起こしモード (`[GEMINI] mode`)

| 値 | 動作 |
|---|---|
| `verbatim` (デフォルト) | 発話どおりに書き起こす。フィラーや言い直しもそのまま残る |
| `smart` | フィラー除去、言い直しの解決、箇条書き・日付・金額の自動整形を行う |

`smart` はモデル側が文章を再構成するため、F9 の句読点トグルや `data/replacements.txt` の置換ルールが想定どおりに効かない場合があります。短文入力用途では `verbatim` を推奨します。

その他のセクションは `config.ini` 内を参照してください。

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 開発者向け情報

### テスト

```bash
python -m pytest tests/ -v --tb=short
python -m pytest tests/ -v --tb=short --cov=app --cov-report=html
```

### 型チェック

```bash
pyright app external_service service utils
```

### 実行ファイルのビルド

PyInstaller を使用して実行ファイルを生成します。

**ビルド方法:**

```bash
python build.py
```

**ビルド内容:**

| 項目 | 詳細 |
|-----|------|
| 出力ファイル | `dist/VoiceTrans/VoiceTrans.exe` |
| 含まれるファイル | `utils/config.ini`、`data/replacements.txt`、`data/technical_terms.txt` |
| アイコン | `assets/VoiceTrans.ico` |

**ビルド後:**

1. `dist/VoiceTrans/VoiceTrans.exe` が生成されます
2. 同じディレクトリに必要なファイルが自動的に配置されます
3. `VoiceTrans.exe` をダブルクリックで起動可能

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## システム要件

- Windows 11
- Python 3.13 以上
- マイク入力デバイス
- Gemini API キー

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 使用料金について

本ツールは **Gemini API (`gemini-3.5-transcribe`)** を使用するため、API の利用に応じた使用料金が発生します。

- 使用料金の詳細は [Gemini API の料金ページ](https://ai.google.dev/gemini-api/docs/pricing) にてご確認ください。

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## トラブルシューティング

### API キーエラーが表示される

- `%APPDATA%\VoiceTrans\.env` に `GEMINI_API_KEY` が正しく設定されているか確認
- [Google AI Studio](https://aistudio.google.com/apikey) で API キーが有効かどうかを確認

### 音声が録音されない

1. Windows の設定でマイクが有効か確認
2. 他のアプリがマイクを占有していないか確認
3. PyAudio の動作確認: `python -c "import pyaudio; print('OK')"`

### テキスト貼り付けが機能しない

1. 貼り付けは pynput のキーボードコントローラーで Ctrl+V を送信します。貼り付け先アプリが Ctrl+V による標準的なテキスト入力に対応しているか確認
2. 貼り付け先が管理者権限で実行されている場合、同じく管理者権限で VoiceTrans を起動する
3. 貼り付けが途切れる場合は `utils/config.ini` の `[CLIPBOARD] paste_delay` を大きくする

### HTTP 429 エラー（Gemini API レート制限超過）

Gemini API は **1 分間に 10 リクエスト** というレート制限があります。短時間に連続で文字起こしを行う場合に HTTP 429 エラーが発生することがあります。

**対策:**
- 文字起こしのリクエストを間隔を空けて送信する（1 分間に最大 10 回）
- エラーが発生した場合は数秒待機してから F8 キーで再送信してください
- 1 回あたりの録音をまとめて長くし、リクエスト回数そのものを減らす（`utils/config.ini` の `[RECORDING] auto_stop_timer` で自動停止までの秒数を調整）

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## ライセンス

ライセンス情報は [LICENSE](docs/LICENSE) を参照してください。

## 更新履歴

更新履歴は [CHANGELOG.md](docs/CHANGELOG.md) を参照してください。

## 免責事項
Gemini API をご利用の際は、個人を特定できる医療情報は入力しないでください。

本ツールは、Gemini API を通じた音声データの取り扱いに起因するいかなる損害についても、責任を負いかねます。

詳細は、Google の公式サイトにてプライバシーポリシーおよび利用規約をご確認ください。

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>
