import json
import urllib.request
import re
from pathlib import Path
from typing import List, Dict
import yt_dlp


class SubtitleFetcher:
    """YouTube 用の字幕を取得するクラス。
    yt-dlp を使用して字幕 URL を解決し、Web から VTT データをダウンロードしてパースする。
    日本語手動 -> 日本語自動生成 -> 他言語から日本語への自動翻訳 -> 他言語オリジナル の順で試みる。
    """

    def __init__(self, url: str, video_id: str, lang: str = "ja", cache_dir: Path = Path("cache")):
        self.url = url
        self.video_id = video_id
        self.lang = lang
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / f"{video_id}_{lang}.json"

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
        """yt-dlp を用いて字幕 URL を解決し、ダウンロードしてパースする。"""
        # yt-dlp でメタデータを取得
        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            try:
                info = ydl.extract_info(self.url, download=False)
            except Exception as e:
                print(f"yt-dlp によるメタデータの取得に失敗しました: {e}")
                return []

        subtitles = info.get("subtitles", {})
        auto_captions = info.get("automatic_captions", {})

        target_url = None
        needs_translation = False

        # --- 優先順位に従って字幕URLを探す ---
        
        # 1. 日本語の手動字幕
        if self.lang in subtitles:
            target_url = self._get_vtt_url(subtitles[self.lang])
        
        # 2. 日本語の自動生成字幕
        if not target_url and self.lang in auto_captions:
            target_url = self._get_vtt_url(auto_captions[self.lang])

        # 3. 他言語の字幕があり、日本語への自動翻訳が可能な場合
        # (手動字幕の他言語から探す)
        if not target_url:
            for l_code, list_entries in subtitles.items():
                url = self._get_vtt_url(list_entries)
                if url:
                    target_url = url
                    needs_translation = True
                    break

        # (自動生成の他言語から探す)
        if not target_url:
            for l_code, list_entries in auto_captions.items():
                url = self._get_vtt_url(list_entries)
                if url:
                    target_url = url
                    needs_translation = True
                    break

        if not target_url:
            print("利用可能な字幕が見つかりませんでした。")
            return []

        # 自動翻訳パラメータを付与
        if needs_translation:
            # URLに &tlang=ja (または指定言語) を追加して自動翻訳させる
            connector = "&" if "?" in target_url else "?"
            target_url = f"{target_url}{connector}tlang={self.lang}"
            print(f"他言語字幕を検知したため、自動翻訳 ({self.lang}) を適用します。")

        # 字幕データをダウンロード
        try:
            req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req) as resp:
                vtt_content = resp.read().decode("utf-8")
            return self._parse_vtt(vtt_content)
        except Exception as e:
            print(f"字幕データのダウンロードまたはパースに失敗しました: {e}")
            return []

    def _get_vtt_url(self, formats_list: List[Dict]) -> str:
        """フォーマットリストから vtt 形式の URL を抽出する。"""
        for fmt in formats_list:
            if fmt.get("ext") == "vtt":
                return fmt.get("url")
        # vtt がない場合は最初のものを返す（フォールバック）
        if formats_list:
            return formats_list[0].get("url")
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

