import json
import re
import subprocess
import os
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
        try:
            print(f"字幕ダウンロード中: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                print(f"yt-dlp エラー: {result.stderr}")
                return None
            
            print(f"yt-dlp 出力: {result.stdout}")
            
            # ダウンロードされたファイルを探す
            vtt_files = list(self.temp_dir.glob("*.vtt"))
            if vtt_files:
                vtt_file = vtt_files[0]  # 最初の VTT ファイルを使用
                print(f"VTT ファイルを取得しました: {vtt_file}")
                return str(vtt_file)
            else:
                print(f"VTT ファイルが見つかりません。タイプ: {subtitle_type}, 言語: {lang}")
                return None
                
        except subprocess.TimeoutExpired:
            print("yt-dlp コマンドがタイムアウトしました。")
            return None
        except FileNotFoundError:
            print("yt-dlp コマンドが見つかりません。インストールしてください: pip install yt-dlp")
            return None
        except Exception as e:
            print(f"yt-dlp 実行中にエラーが発生しました: {e}")
            return None

    def _parse_vtt(self, vtt_text: str) -> List[Dict]:
        """WebVTT 形式のテキストを解析してリスト `[{"start": float, "text": str}]` に変換する。"""
        lines = vtt_text.splitlines()
        entries = []
        
        # タイムスタンプ行パターン: "00:01:23.456 --> 00:01:25.789" または "01:23.456 --> 01:25.789"
        time_pattern = re.compile(r'(?:(\d{2}):)?(\d{2}):(\d{2})[.,](\d{3})\s+-->\s+')
        
        current_start = None
        current_text_lines = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if current_start is not None and current_text_lines:
                    text = " ".join(current_text_lines).strip()
                    # <c>タグやスタイルタグなどの除去
                    text = re.sub(r'<[^>]+>', '', text)
                    # 重複スペースの除去
                    text = re.sub(r'\s+', ' ', text)
                    if text:
                        entries.append({"start": current_start, "text": text})
                    current_start = None
                    current_text_lines = []
                continue
                
            match = time_pattern.match(line)
            if match:
                # タイムスタンプ部分をパースして秒に変換
                time_str = line.split("-->")[0].strip()
                parts = time_str.split(":")
                if len(parts) == 3: # hh:mm:ss.mmm
                    h, m, s = parts
                    sec = float(h) * 3600 + float(m) * 60 + float(s.replace(',', '.'))
                elif len(parts) == 2: # mm:ss.mmm
                    m, s = parts
                    sec = float(m) * 60 + float(s.replace(',', '.'))
                else:
                    sec = 0.0
                current_start = sec
            elif current_start is not None:
                # ヘッダー行やメタデータなどを除外
                if not line.startswith("WEBVTT") and not line.startswith("Kind:") and not line.startswith("Language:"):
                    current_text_lines.append(line)
                    
        # 最後のブロックを処理
        if current_start is not None and current_text_lines:
            text = " ".join(current_text_lines).strip()
            text = re.sub(r'<[^>]+>', '', text)
            text = re.sub(r'\s+', ' ', text)
            if text:
                entries.append({"start": current_start, "text": text})
                
        return entries

