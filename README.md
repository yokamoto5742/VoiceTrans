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

- **Google Cloud Speech-to-Text API** による高い日本語認識精度
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

`data/technical_terms.txt` に専門用語を登録すると、Google Cloud Speech-to-Text API にフレーズヒントとして送信され、認識精度が向上します。

### 登録方法

`data/technical_terms.txt` に 1 行 1 フレーズで登録します。

```
$OOV_CLASS_DIGIT_SEQUENCE
$OPERAND
加齢黄斑変性
```

- **クラストークン** (`$OOV_CLASS_*`) — Google STT API の特殊トークン。数字列や演算子など、クラスベースの認識ヒント
- **テキストフレーズ** — 医療用語や業界用語など、固有の専門用語

### 実装動作

アプリケーション起動時に `data/technical_terms.txt` を読み込み、STT API へ `speech_recognition_hints` として設定されます。これにより以下のような効果が期待できます。

- 医療系の専門用語（「加齢黄斑変性」など）の誤認識を削減
- 部署名や業務用語の正確な認識

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 置換ルールのサンプル

`data/replacements.txt` に CSV 形式で登録します。実際の運用例を抜粋します。

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

### 3. Google Cloud API キーを設定

`.env` の`GOOGLE_CREDENTIALS_JSON` の値には、Google Cloud Console からダウンロードしたサービスアカウントキーの JSON を**1 行に変換した文字列**が必要です。

#### 3-1. サービスアカウントキーを 1 行に変換

Google Cloud Console からダウンロードした JSON ファイルには改行が含まれているため、`scripts/json_minifier.py` を使って 1 行に変換します。

```bash
python scripts/json_minifier.py
```

実行するとファイル選択ダイアログが開きます。Google Cloud のサービスアカウントキー JSON ファイルを選択してください。

スクリプトは変換後の 1 行 JSON をタイムスタンプ付きで出力ファイル（例: `credentials_20240430_123456.json`）に保存します。出力ファイル内の JSON 文字列をコピーしてください。

#### 3-2. .env ファイルを作成

```
GOOGLE_PROJECT_ID=my-awesome-app-123456
GOOGLE_LOCATION=asia-northeast1
GOOGLE_CREDENTIALS_JSON={"type":"service_account","project_id":"my-awesome-app-123456","private_key_id":...}
```

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
- **`external_service/`** — Google Cloud API の薄いラッパー
- **`utils/`** — 設定 (`AppConfig`)、ロギング、クラッシュログ、シグナル設定

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 設定

### 主要な設定 (utils/config.ini)

| セクション | 用途 |
|-----------|------|
| `[GOOGLE_STT]` | モデル (`chirp_3`)、言語 (`ja-JP`)、専門用語フレーズセット |
| `[KEYS]` | ショートカット割り当て (Pause: 録音、F8: 再変換、F9: 句読点切替、Esc: 終了) |
| `[RECORDING]` | 自動停止タイマー（デフォルト 60 秒） |
| `[PATHS]` | 置換ルールファイル、一時ファイル保存先 |

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
pyright app service utils
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
- Python 3.12 以上
- マイク入力デバイス
- Google Cloud の credentials.json 

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## 使用料金について

本ツールは **Google Cloud Speech-to-Text API** を使用するため、API の利用に応じた使用料金が発生します。

- Speech-to-Text V2 API 標準認識モデルの使用料金の詳細は [Google Cloud の公式サイト](https://cloud.google.com/speech-to-text/pricing) にてご確認ください。

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## トラブルシューティング

### API キーエラーが表示される

- `.env`に`GOOGLE_CREDENTIALS_JSON` が正しく設定されているか確認
- Google Cloud ダッシュボードで認証情報が有効かどうかを確認

### 音声が録音されない

1. Windows の設定でマイクが有効か確認
2. 他のアプリがマイクを占有していないか確認
3. PyAudio の動作確認: `python -c "import pyaudio; print('OK')"`

### テキスト貼り付けが機能しない

1. `utils/config.ini` で `use_sendinput = True` を確認
2. 貼り付け先アプリが標準的なテキスト入力に対応しているか確認

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>

---

## ライセンス

ライセンス情報は [LICENSE](docs/LICENSE) を参照してください。

## 更新履歴

更新履歴は [CHANGELOG.md](docs/CHANGELOG.md) を参照してください。

## 免責事項
Google Cloud Speech-to-Textをご利用の際は、個人を特定できる医療情報は入力しないでください。 

本ツールは、Google Cloud Speech-to-Textを通じた音声データの取り扱いに起因するいかなる損害についても、責任を負いかねます。

詳細は、Google Cloudの公式サイトにてプライバシーポリシーおよび利用規約をご確認ください。

<div align="right"><a href="#目次">▲ 目次へ戻る</a></div>
"# VoiceTrans" 
