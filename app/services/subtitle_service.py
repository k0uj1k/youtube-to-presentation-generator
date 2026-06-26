import json
import re
import subprocess
import os
import time
from pathlib import Path
from typing import List, Dict


class SubtitleFetcher:
    """YouTube 用の字幕を取得するクラス。
    yt-dlp コマンドラインツールで .vtt ファイルをローカルダウンロードしてパースする。
    日本語手動 -> 日本語自動生成 -> 他言語オリジナル の順で試みる。
    """

    def __init__(self, url: str, video_id: str, lang: str = "ja", 
                 cache_dir: Path = Path("cache"), 
                 temp_dir: Path = None):
        self.url = url
        self.video_id = video_id
        self.lang = lang
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / f"{video_id}_{lang}.json"
        
        # 一時ディレクトリ（VTT ファイルダウンロード先）
        if temp_dir is None:
            temp_dir = Path(__file__).parent / "temp_data" / video_id
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def fetch(self) -> List[Dict]:
        """字幕を取得し、リスト `[{"start": float, "text": str}, ...]` で返す。
        キャッシュがあればそれを利用する。
        """
        # 1. キャッシュがあればロードして返す
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"キャッシュの読み込みに失敗しました: {e}")

        # 2. 字幕の取得処理
        try:
            entries = self._get_subtitles_from_youtube()
            if entries:
                # キャッシュに保存
                with open(self.cache_file, "w", encoding="utf-8") as f:
                    json.dump(entries, f, ensure_ascii=False, indent=2)
                return entries
        except Exception as e:
            print(f"字幕の取得中にエラーが発生しました: {e}")

        return []

    def _get_subtitles_from_youtube(self) -> List[Dict]:
        """yt-dlp コマンドラインツールで .vtt ファイルをダウンロードしてパースする。"""
        vtt_file = None
        
        # === 優先順位 1: 日本語の手動字幕 ===
        vtt_file = self._download_vtt_with_ytdlp(
            subtitle_type="manual",
            lang=self.lang
        )
        
        # === 優先順位 2: 日本語の自動生成字幕 ===
        if not vtt_file:
            vtt_file = self._download_vtt_with_ytdlp(
                subtitle_type="auto",
                lang=self.lang
            )
        
        # === 優先順位 3: 他言語の手動字幕（オリジナル）===
        if not vtt_file:
            vtt_file = self._download_vtt_with_ytdlp(
                subtitle_type="manual",
                lang=None  # 利用可能な言語を自動選択
            )
        
        # === 優先順位 4: 他言語の自動生成字幕（オリジナル）===
        if not vtt_file:
            vtt_file = self._download_vtt_with_ytdlp(
                subtitle_type="auto",
                lang=None
            )
        
        if not vtt_file:
            print("利用可能な字幕が見つかりませんでした。")
            return []
        
        # VTT ファイルをパース
        try:
            with open(vtt_file, "r", encoding="utf-8") as f:
                vtt_content = f.read()
            return self._parse_vtt(vtt_content)
        except Exception as e:
            print(f"VTT ファイルの読み込みまたはパースに失敗しました: {e}")
            return []
    
    def _download_vtt_with_ytdlp(self, subtitle_type: str = "auto", lang: str = None) -> str:
        """yt-dlp コマンドで VTT ファイルをダウンロードする。
        
        Parameters
        ----------
        subtitle_type : str
            'auto' = 自動生成字幕, 'manual' = 手動字幕
        lang : str or None
            言語コード（'ja', 'en' など）。None の場合は利用可能な言語を自動選択。
        
        Returns
        -------
        str
            ダウンロードされた VTT ファイルのパス。ない場合は None。
        """
        # 既存の古い VTT ファイルを削除してクリーンにする
        if self.temp_dir.exists():
            for f in self.temp_dir.glob("*.vtt"):
                try:
                    f.unlink()
                except Exception as e:
                    print(f"古い VTT ファイル {f} のクリーンアップに失敗: {e}")

        # yt-dlp コマンドのオプション構築
        cmd = ["yt-dlp", "--skip-download"]
        
        # 字幕オプション
        if subtitle_type == "manual":
            cmd.append("--write-subs")
        elif subtitle_type == "auto":
            cmd.append("--write-auto-subs")
        
        # VTT 形式を指定
        cmd.append("--sub-format")
        cmd.append("vtt")
        
        # 言語指定（lang が指定されている場合）
        if lang:
            cmd.append("--sub-langs")
            cmd.append(lang)
            lang_suffix = lang
        else:
            lang_suffix = "*"  # 利用可能な言語すべて
        
        # 出力パターン（ファイル名テンプレート）
        # デフォルト: {video_id}.{subtitle_type}.{lang}.vtt
        output_template = os.path.join(str(self.temp_dir), "%(id)s.%(ext)s")
        cmd.append("-o")
        cmd.append(output_template)
        
        # URL
        cmd.append(self.url)
        
        # yt-dlp を実行
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"字幕ダウンロード中 (試行 {attempt + 1}/{max_retries}): {' '.join(cmd)}")
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode != 0:
                    print(f"yt-dlp エラー: {result.stderr}")
                    if attempt < max_retries - 1:
                        print("字幕のダウンロードに失敗しました。3秒後にリトライします。")
                        time.sleep(3)
                        continue
                    return None
                
                print(f"yt-dlp 出力: {result.stdout}")
                
                # ダウンロードされたファイルを探索する
                vtt_pattern = f"{self.video_id}.{lang}.vtt" if lang else f"{self.video_id}.*.vtt"
                vtt_files = list(self.temp_dir.glob(vtt_pattern))
                if not vtt_files:
                    # フォールバックとしてすべての .vtt ファイルを検索
                    vtt_files = list(self.temp_dir.glob("*.vtt"))

                if vtt_files:
                    vtt_file = vtt_files[0]
                    print(f"VTT ファイルを取得しました: {vtt_file}")
                    return str(vtt_file)
                else:
                    print(f"VTT ファイルが見つかりません。タイプ: {subtitle_type}, 言語: {lang}")
                    if attempt < max_retries - 1:
                        print("3秒後にリトライします。")
                        time.sleep(3)
                        continue
                    return None
                    
            except subprocess.TimeoutExpired:
                print("yt-dlp コマンドがタイムアウトしました。")
                if attempt < max_retries - 1:
                    print("3秒後にリトライします。")
                    time.sleep(3)
                    continue
                return None
            except FileNotFoundError:
                print("yt-dlp コマンドが見つかりません。インストールしてください: pip install yt-dlp")
                return None
            except Exception as e:
                print(f"yt-dlp 実行中にエラーが発生しました: {e}")
                if attempt < max_retries - 1:
                    print("3秒後にリトライします。")
                    time.sleep(3)
                    continue
                return None

    def _parse_vtt(self, vtt_text: str) -> List[Dict]:
        """WebVTT 形式のテキストを解析してリスト `[{"start": float, "text": str}]` に変換する。
        ユーザー指定のクレンジングルールを適用し、自動生成字幕特有の重複を排除して読みやすさを向上させる。
        """
        lines = vtt_text.splitlines()
        temp_entries = []
        
        # タイムスタンプ行パターン: "00:01:23.456 --> 00:01:25.789" または "01:23.456 --> 01:25.789"
        time_pattern = re.compile(r'(?:(\d{2}):)?(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+')
        
        current_start = None
        current_text_lines = []
        
        for line in lines:
            line = line.strip()
            
            # 空行、タイムスタンプ（-->）を含む行、数字のみの行、WEBVTTヘッダー、メタデータ行を除外
            if not line or "-->" in line or line.isdigit() or line == "WEBVTT" or line.startswith("Kind:") or line.startswith("Language:"):
                # タイムスタンプ行は時間の抽出に必要なので、ここで判定して処理
                match = time_pattern.match(line)
                if match:
                    # 以前のブロックを確定して保存
                    if current_start is not None and current_text_lines:
                        self._add_clean_entry(temp_entries, current_start, current_text_lines)
                        current_text_lines = []
                    
                    # 新しいタイムスタンプを解析して秒に変換
                    time_str = line.split("-->")[0].strip()
                    parts = time_str.split(":")
                    if len(parts) == 3:  # hh:mm:ss.mmm
                        h, m, s = parts
                        sec = float(h) * 3600 + float(m) * 60 + float(s.replace(',', '.'))
                    elif len(parts) == 2:  # mm:ss.mmm
                        m, s = parts
                        sec = float(m) * 60 + float(s.replace(',', '.'))
                    else:
                        sec = 0.0
                    current_start = sec
                continue
            
            if current_start is not None:
                current_text_lines.append(line)
                
        # 最後のブロックを処理
        if current_start is not None and current_text_lines:
            self._add_clean_entry(temp_entries, current_start, current_text_lines)
            
        # 最終的な entries リストを構築 (raw_text キーを排除)
        entries = []
        for entry in temp_entries:
            entries.append({
                "start": entry["start"],
                "text": entry["text"]
            })
        return entries

    def _add_clean_entry(self, temp_entries: List[Dict], start_time: float, text_lines: List[str]):
        """テキスト行をクレンジングし、重複を排除して一時エントリーリストに追加する。"""
        cleaned_lines = []
        for line in text_lines:
            # タグの除去
            line = re.sub(r'<[^>]+>', '', line).strip()
            # 重複スペースの除去
            line = re.sub(r'\s+', ' ', line)
            if line:
                cleaned_lines.append(line)
                
        if not cleaned_lines:
            return

        # 行を結合
        raw_text = " ".join(cleaned_lines).strip()
        text = raw_text
        
        # 直前のエントリーとの重複排除（自動生成字幕の累積表示対策）
        if temp_entries:
            prev_raw_text = temp_entries[-1]["raw_text"]
            
            # 1. 完全一致なら追加しない
            if raw_text == prev_raw_text:
                return
                
            # 2. 直前のブロックの生のテキストが、今回のテキストの開始部分と一致する場合、重複部分を除去
            if raw_text.startswith(prev_raw_text):
                text = raw_text[len(prev_raw_text):].strip()
            # 3. 今回のテキストが直前のテキストに含まれる場合は追加しない（スクロールアウト対策）
            elif raw_text in prev_raw_text:
                return
                
        if text:
            temp_entries.append({
                "start": start_time,
                "text": text,
                "raw_text": raw_text
            })

