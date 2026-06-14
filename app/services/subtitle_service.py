import json
import urllib.request
from pathlib import Path
from typing import List, Dict

from bs4 import BeautifulSoup


class SubtitleFetcher:
    import logging
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')
    """YouTube 用の字幕を取得するクラス。
    `https://www.youtube.com/api/timedtext` エンドポイントから JSON3 または XML を取得し、
    字幕リスト `[{"start": float, "text": str}, ...]` を返す。
    キャッシュ機構を備えており、同一 video_id と言語の字幕はローカルに保存して再利用できる。
    """

    def __init__(self, video_id: str, lang: str = "ja", cache_dir: Path = Path("cache")):
        self.video_id = video_id
        self.lang = lang
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_file = self.cache_dir / f"{video_id}_{lang}.json"

    def _download_subtitles(self) -> str:
        """字幕を HTTP で取得し、キャッシュに保存する。言語指定が失敗した場合は自動生成字幕 (kind=asr) を試す。"""
        # キャッシュがあれば再利用
        if self.cache_file.exists():
            return self.cache_file.read_text(encoding="utf-8")
        base_url = f"https://www.youtube.com/api/timedtext?v={self.video_id}&fmt=json3"
        # 試行順序: 日本語 (self.lang) -> 英語 -> 自動生成字幕 (ASR)
        attempts = [
            ("lang", f"{base_url}&lang={self.lang}"),
            ("english", f"{base_url}&lang=en"),
            ("asr", f"{base_url}&kind=asr"),
        ]
        for kind, url in attempts:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req) as resp:
                    content = resp.read().decode("utf-8")
                if content.strip():
                    # 保存して返す
                    self.cache_file.write_text(content, encoding="utf-8")
                    return content
            except Exception as e:
                logging.debug(f"字幕取得 ({kind}) 失敗: {e}")
        # すべて失敗した場合は例外を送出
        raise RuntimeError("字幕が取得できませんでした。動画に字幕が無い可能性があります。")
# (旧実装削除: 新しい _download_subtitles が上部で定義されています)

    def _parse(self, content: str) -> List[Dict]:
        """取得した文字列を JSON または XML として解析し、字幕エントリを作成する。"""
        # まず JSON としてパースを試みる（json3 フォーマット）
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # JSON 解析に失敗したら XML とみなす
            soup = BeautifulSoup(content, "xml")
            entries: List[Dict] = []
            for txt in soup.find_all("text"):
                start = float(txt.get("start", "0"))
                text = txt.string if txt.string is not None else ""
                # HTML エンティティの簡易置換
                text = text.replace("&#39;", "'").replace("&amp;", "&")
                entries.append({"start": start, "text": text})
            entries.sort(key=lambda x: x["start"])
            return entries
        # JSON3 フォーマットを処理
        events = data.get("events", [])
        entries: List[Dict] = []
        for ev in events:
            start_ms = ev.get("tStartMs")
            if start_ms is None:
                continue
            start = start_ms / 1000.0
            segs = ev.get("segs", [])
            if not segs:
                continue
            text = segs[0].get("utf8", "")
            entries.append({"start": start, "text": text})
        entries.sort(key=lambda x: x["start"])
        return entries

    def fetch(self) -> List[Dict]:
        """字幕を取得し、リストで返す。エラー時は空リストを返す。"""
        try:
            content = self._download_subtitles()
            return self._parse(content)
        except Exception as e:
            print(f"字幕取得に失敗しました: {e}")
            return []
