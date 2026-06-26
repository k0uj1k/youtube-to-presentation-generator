# TODO

## コードレビュー指摘事項

### 高

- [x] **TODO-001: ファイル配信パスの検証を強化する**
  - 対象ファイル: `app/main.py`
  - 現在の `os.path.basename()` 処理は `..` を拒否しないため、`/api/images/../gemini_service.py` のようなパスで意図したタスクディレクトリ外へ抜けられる可能性がある。
  - `task_id` を UUID 形式に制限し、ファイル名を検証し、解決後のパスが必ず `TEMP_DIR` 配下にあることを確認する。

- [x] **TODO-002: Gemini 要約を本当に任意機能として安全に扱う**
  - 対象ファイル: `app/services/gemini_service.py`, `app/services/youtube_service.py`
  - `Optional` と `Dict` が import されないまま使われている。
  - `Dict[str, any]` は `typing` の `Any` を使うべき。
  - `youtube_service.py` は `GeminiSummarizer` 初期化時に `ValueError` しか捕捉していないため、SDK 起因のエラーで PPTX 生成全体が失敗し、元字幕へのフォールバックが効かない可能性がある。
  - 必要な型 import を追加し、任意機能として想定される Gemini 初期化失敗を適切に捕捉する。

### 中

- [x] **TODO-003: フレームキャッシュのメモリ使用量を削減する**
  - 対象ファイル: `app/services/youtube_service.py`
  - 対応済み: `frame_storage` を使ったフル解像度フレームの大量保持をやめ、基準フレームとの差分でスライド切替を検出して即時保存する方式に変更した。

- [ ] **TODO-004: 生成タスクデータと字幕キャッシュのクリーンアップを追加する**
  - 対象ファイル: `app/services/youtube_service.py`, `app/services/subtitle_service.py`
  - 一時動画ファイルは削除されるが、生成画像、PPTX、VTT、字幕キャッシュは無期限に残る。
  - TTL による削除、またはタスク単位のクリーンアップ処理を追加する。

- [x] **TODO-005: Gemini SDK の API スタイルを統一する**
  - 対象ファイル: `app/services/gemini_service.py`
  - コードは先に `google.genai` を import しているが、呼び出しは `google.generativeai` の `configure()` と `GenerativeModel()` に依存している。
  - `google-generativeai` のみに寄せるか、新しい `google.genai` クライアント用の実装に更新する。

- [ ] **TODO-006: ダウンロード前に YouTube URL を検証・正規化する**
  - 対象ファイル: `app/services/youtube_service.py`
  - `extract_video_id()` は YouTube 風の 11 文字 ID を含む任意の文字列を受け付けるが、`download_video()` は元の URL をそのまま `yt-dlp` に渡している。
  - 許可する YouTube ホストを検証するか、抽出した ID から `https://www.youtube.com/watch?v=<video_id>` の正規 URL を組み立てる。

- [ ] **TODO-007: VTT 字幕ファイルの選択を決定的にする**
  - 対象ファイル: `app/services/subtitle_service.py`
  - `_download_vtt_with_ytdlp()` は一時ディレクトリ内の最初の `*.vtt` を使うため、古いファイルや別言語のファイルを選ぶ可能性がある。
  - ダウンロード前に対象ディレクトリを掃除するか、期待する出力ファイルを厳密に選択する。

- [x] **TODO-010: MAD閾値を 1.0 - 15.0 - 100.0 に設定**


- [ ] **TODO-008: リクエスト値の範囲検証を追加する**
  - 対象ファイル: `app/main.py`
  - `change_level` が API スキーマ層で制約されていない。
  - Pydantic の `Field` 制約を使い、例として `1 <= change_level <= 10` を保証する。

- [ ] **TODO-009: 依存関係と実行環境のセットアップを揃える**
  - 対象ファイル: `requirements.txt`, `README.md`, `setup.bat`, `wheelhouse/`
  - 現在の環境には `fastapi` がインストールされておらず、`requirements.txt` のバージョンと `wheelhouse` 内の一部 wheel のバージョンも一致していない。
  - 対応 Python バージョン、固定依存バージョン、オフライン wheel の内容を揃え、再現可能なセットアップにする。

## 検証メモ

- `python -m py_compile app\main.py app\services\youtube_service.py app\services\subtitle_service.py app\services\gemini_service.py` は、Python が `__pycache__` に書き込めず失敗した。
- `PYTHONDONTWRITEBYTECODE=1` を指定した import 検証は、現在の環境に `fastapi` がインストールされていないため完了できなかった。
