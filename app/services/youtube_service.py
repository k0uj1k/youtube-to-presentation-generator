import os
import re
import uuid
import subprocess
import cv2
import numpy as np
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound
import yt_dlp
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import unicodedata
# from .gemini_service import GeminiSummarizer

# 一時ファイルを保存するディレクトリ
TEMP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "temp_data")
os.makedirs(TEMP_DIR, exist_ok=True)

# 変化レベル（1〜10）を MAD 閾値に変換するテーブル
# レベル 1 = 非常に敏感（わずかな変化も検知）、10 = 鈍感（大きな変化のみ検知）
_CHANGE_LEVEL_TO_THRESHOLD = {
    1:  1.0,
    2:  2.5,
    3:  4.0,
    4:  6.0,
    5:  8.5,
    6: 11.0,
    7: 14.0,
    8: 18.0,
    9: 23.0,
   10: 30.0,
}


def sanitize_filename(title: str, max_length: int = 200) -> str:
    """
    動画タイトルをファイルシステムセーフなファイル名に変換する。
    
    - Unicode正規化（NFKC）
    - ファイルシステムで禁止されている文字を削除
    - 先頭/末尾の空白やドットを削除
    - 最大文字数を制限
    """
    if not title:
        return "presentation"
    
    # Unicode正規化（濁音などを統一）
    title = unicodedata.normalize('NFKC', title)
    
    # ファイルシステムで禁止されている文字を削除・置換
    # Windows: < > : " / \ | ? *
    # macOS/Linux: /
    forbidden_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(forbidden_chars, '', title)
    
    # 連続する空白をシングルスペースに
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # 先頭/末尾の空白やドットを削除（ファイルシステムの要件）
    sanitized = sanitized.strip('. ')
    
    # 最大文字数を制限（.pptx を考慮）
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length].strip()
    
    # 万が一空文字列になった場合のフォールバック
    if not sanitized:
        sanitized = "presentation"
    
    return sanitized


def extract_video_id(url: str) -> str:
    """
    YouTubeのURLから動画IDを抽出する。
    """
    # クエリパラメータ v= から抽出
    if "v=" in url:
        match = re.search(r"v=([0-9A-Za-z_-]{11})", url)
        if match:
            return match.group(1)

    # shortsのURLから抽出 (/shorts/xxx)
    if "/shorts/" in url:
        match = re.search(r"/shorts/([0-9A-Za-z_-]{11})", url)
        if match:
            return match.group(1)

    # youtu.be/xxx から抽出
    if "youtu.be/" in url:
        match = re.search(r"youtu\.be/([0-9A-Za-z_-]{11})", url)
        if match:
            return match.group(1)

    # その他のURLパターンからのフォールバック抽出
    patterns = [
        r"embed\/([0-9A-Za-z_-]{11})",
        r"\/([0-9A-Za-z_-]{11})"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)

    raise ValueError("無効なYouTube URLです。")


def get_transcript(url: str, video_id: str) -> list:
    """
    動画の字幕（文字起こし）を取得する。
    日本語の手動字幕 → 自動生成 → 英語 → SubtitleFetcher の順で試みる。
    すべて失敗した場合は空リストを返す（字幕なしで処理続行可能）。
    """
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
        # 1. 手動字幕（日本語）
        try:
            transcript = transcript_list.find_transcript(['ja'])
            return transcript.fetch()
        except NoTranscriptFound:
            pass
        # 2. 自動生成字幕（日本語）
        try:
            generated = transcript_list.find_generated_transcript(['ja'])
            return generated.fetch()
        except NoTranscriptFound:
            pass
        # 3. 手動字幕（英語）
        try:
            transcript = transcript_list.find_transcript(['en'])
            return transcript.fetch()
        except NoTranscriptFound:
            pass
        # 4. 自動生成字幕（英語）
        try:
            generated = transcript_list.find_generated_transcript(['en'])
            return generated.fetch()
        except NoTranscriptFound:
            pass
        # 5. 任意の利用可能な字幕（最初のもの）
        for t in transcript_list:
            return t.fetch()
    except (TranscriptsDisabled, Exception) as e:
        print(f"字幕の取得に失敗しました (youtube_transcript_api): {e}")

    # Fallback: HTTP 取得（yt-dlpを使用した解決と自動翻訳対応）
    from .subtitle_service import SubtitleFetcher
    fetcher = SubtitleFetcher(url, video_id, lang="ja")
    return fetcher.fetch()


def download_video(url: str, output_path: str) -> str:
    """
    yt-dlpを使用して画像抽出用に高精細な動画（例: 1080p）をダウンロードする。
    """
    ydl_opts = {
        'format': 'bestvideo[height<=1080][ext=mp4]/best[height<=1080][ext=mp4]/best[ext=mp4]',  # 高画質なスライド画像抽出のため1080p以下の最高画質MP4を選択
        'outtmpl': output_path,
        'quiet': True,
        'no_warnings': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return info.get('title', 'YouTube Video')
    except yt_dlp.utils.DownloadError as e:
        error_msg = str(e)
        if "Video unavailable" in error_msg:
            raise ValueError("指定された動画は存在しないか、非公開、あるいは地域制限によりアクセスできません。")
        else:
            raise ValueError(f"動画のダウンロードに失敗しました: {error_msg}")
    except Exception as e:
        raise ValueError(f"動画のダウンロード処理中に予期せぬエラーが発生しました: {str(e)}")


def get_keyframe_timestamps(video_path: str) -> list:
    """
    ffprobe を使用して Closed GOP の I フレーム（キーフレーム）の
    タイムスタンプ（秒）リストを返す。
    パケットレベルで K フラグ（key_frame）を持つフレームのみを抽出する。
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "packet=pts_time,flags",
        "-of", "csv=print_section=0",
        video_path
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )
    except FileNotFoundError:
        # ffprobe が見つからない場合は空リストを返す（フォールバックで対処）
        print("ffprobe が見つかりません。PATH に ffmpeg/ffprobe を追加してください。")
        return []
    except subprocess.TimeoutExpired:
        print("ffprobe がタイムアウトしました。")
        return []

    timestamps = []
    for line in result.stdout.splitlines():
        parts = line.strip().split(",")
        if len(parts) < 2:
            continue
        pts_str = parts[0]
        flags = parts[1] if len(parts) > 1 else ""
        # "K" フラグ = キーフレーム（I フレーム）
        if "K" in flags.upper():
            try:
                timestamps.append(float(pts_str))
            except ValueError:
                pass

    return sorted(set(timestamps))


def get_keyframe_timestamps_cached(video_path: str, cap: cv2.VideoCapture) -> list:
    """
    ffprobe を使用してキーフレームを取得。
    キャッシュ機構で重複呼び出しを回避。
    フォールバック時も同じ VideoCapture インスタンスを活用。
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "packet=pts_time,flags",
        "-of", "csv=print_section=0",
        video_path
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # タイムアウト短縮
        )
        timestamps = []
        for line in result.stdout.splitlines():
            parts = line.strip().split(",")
            if len(parts) >= 2 and "K" in parts[1].upper():
                try:
                    timestamps.append(float(parts[0]))
                except ValueError:
                    pass
        if timestamps:
            return sorted(set(timestamps))
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    # フォールバック: 1秒間隔でサンプリング
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, int(fps))
    return [i / fps for i in range(0, total_frames, step)]


def detect_static_scenes(
    video_path: str,
    min_static_duration: float = 10.0,
    change_level: int = 5
) -> tuple:
    """
    Closed GOP の I フレーム（キーフレーム）のみを参照して、
    min_static_duration 秒以上変化がない静止区間を検知し、代表フレームを抽出する。
    
    【高速化】
    - ビデオスキャンを完全に1回に統一
    - フレームキャッシング機構を導入（代表フレーム抽出時に再ロード不要）
    - メモリ効率とスピードのバランスを最適化

    Parameters
    ----------
    video_path : str
        解析対象の動画ファイルパス。
    min_static_duration : float
        静止区間と判定するための最小継続時間（秒）。
    change_level : int
        変化検知の感度レベル（1〜10）。
        1 = 非常に敏感（わずかな変化も検知）、
        10 = 鈍感（大きな変化のみ検知）。

    Returns
    -------
    tuple[list, str]
        (scenes, task_temp_dir)
        scenes: [{"timestamp": float, "image_path": str}, ...]
    """
    # 変化レベルを MAD 閾値に変換
    change_level = max(1, min(10, int(change_level)))
    threshold = _CHANGE_LEVEL_TO_THRESHOLD[change_level]
    print(f"変化レベル: {change_level} → MAD 閾値: {threshold:.1f}")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("動画ファイルを開けませんでした。")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0

    print(f"動画解析開始: FPS={fps:.2f}, 総フレーム数={total_frames}, 長さ={duration:.2f}秒")

    # I フレームのタイムスタンプを取得（改善版）
    print("I フレーム（キーフレーム）のタイムスタンプを取得中...")
    keyframe_times = get_keyframe_timestamps_cached(video_path, cap)
    print(f"参照する I フレーム数: {len(keyframe_times)}")

    # === 【高速化】フレームスキップ + 遡り確認ロジック ===
    skip_rate = 2  # 2置きで処理（フレーム処理数 50% 削減）
    frame_diffs = []   # (timestamp, mad) のリスト
    prev_gray_small = None
    skipped_frames = []  # スキップされたフレーム情報を一時保存
    
    # フレーム情報をこの辞書に保存（タイムスタンプ -> (BGR画像, グレースケール縮小版)）
    frame_storage = {}
    
    print(f"各Iフレームを処理中... (フレームスキップ率: {skip_rate}置き)")
    processed_count = 0
    skipped_count = 0
    lookback_count = 0
    
    for i, ts in enumerate(keyframe_times):
        # 進捗表示（10%刻み）
        if (i + 1) % max(1, len(keyframe_times) // 10) == 0:
            print(f"  進捗: {i+1}/{len(keyframe_times)} ({(i+1)*100//len(keyframe_times)}%)")
        
        frame_idx = int(ts * fps)
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            continue

        # 高速化のために縮小（160×90）
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray_small = cv2.resize(gray, (160, 90))
        
        # 【高速化】フレームスキップ適用
        if i % skip_rate != 0:
            skipped_frames.append((ts, frame, gray_small))
            skipped_count += 1
            continue
        
        # 通常フレーム（スキップされていないもの）の処理
        mad = 0.0
        if prev_gray_small is not None:
            diff = cv2.absdiff(gray_small, prev_gray_small)
            mad = float(np.mean(diff))
            
            # 【遡り確認】変化が大きい場合、スキップしたフレームも確認
            change_threshold = threshold * 1.5
            if mad >= change_threshold and skipped_frames:
                print(f"  → 大きな変化検出 (MAD={mad:.1f}) タイムスタンプ {ts:.2f}秒で遡り確認開始")
                for skip_ts, skip_frame, skip_gray_small in skipped_frames:
                    mad_skip = float(np.mean(cv2.absdiff(skip_gray_small, prev_gray_small)))
                    frame_diffs.append((skip_ts, mad_skip))
                    frame_storage[skip_ts] = (skip_frame, skip_gray_small)
                    lookback_count += 1
        else:
            mad = 0.0  # 最初のフレームは差分 0

        frame_diffs.append((ts, mad))
        
        # フレームを保存（後で代表フレーム抽出に利用）
        frame_storage[ts] = (frame, gray_small)
        
        prev_gray_small = gray_small
        processed_count += 1
        skipped_frames = []  # スキップフレーム情報をリセット

    cap.release()
    print(f"フレーム処理完了: {processed_count} フレーム処理, {skipped_count} フレームスキップ, {lookback_count} フレーム遡り確認済み")

    # 静止区間（差分が閾値以下の連続フレーム群）を検出
    static_mask = [mad < threshold for (_, mad) in frame_diffs]
    timestamps_list = [ts for (ts, _) in frame_diffs]

    static_intervals = []   # 各要素は [idx1, idx2, ...] のリスト
    current_interval = []

    for idx, (ts, is_static) in enumerate(zip(timestamps_list, static_mask)):
        if is_static:
            current_interval.append(idx)
        else:
            if current_interval:
                # 区間の継続時間を確認
                t_start = timestamps_list[current_interval[0]]
                t_end = timestamps_list[current_interval[-1]]
                if (t_end - t_start) >= min_static_duration:
                    static_intervals.append(current_interval)
            current_interval = []

    # ループ終了後の最後の区間を処理
    if current_interval:
        t_start = timestamps_list[current_interval[0]]
        t_end = timestamps_list[current_interval[-1]]
        if (t_end - t_start) >= min_static_duration:
            static_intervals.append(current_interval)

    print(f"静止区間検出: {len(static_intervals)} 区間を検出")

    # === 【高速化】キャッシュ済みフレームで代表フレームを抽出 ===
    scenes = []
    task_id = str(uuid.uuid4())
    task_temp_dir = os.path.join(TEMP_DIR, task_id)
    os.makedirs(task_temp_dir, exist_ok=True)

    last_extracted_img = None

    print("代表フレームを抽出中...")
    for interval_idx, interval in enumerate(static_intervals):
        # 静止区間の中央インデックスを採用
        mid_pos = interval[len(interval) // 2]
        timestamp = timestamps_list[mid_pos]

        # キャッシュからフレーム取得
        if timestamp not in frame_storage:
            print(f"  警告: タイムスタンプ {timestamp:.2f}秒はキャッシュにありません")
            continue
        
        frame, gray_small = frame_storage[timestamp]

        # 直前の抽出画像との重複チェック
        if last_extracted_img is not None:
            diff = cv2.absdiff(gray_small, last_extracted_img)
            similarity = np.mean(diff)
            if similarity < 3.0:
                print(f"  スキップ: タイムスタンプ {timestamp:.2f}秒は直前と類似度が高い (差分={similarity:.1f})")
                continue

        # 画像を保存
        img_name = f"slide_{interval_idx}_{int(timestamp)}.jpg"
        img_path = os.path.join(task_temp_dir, img_name)
        cv2.imwrite(img_path, frame)

        scenes.append({
            "timestamp": timestamp,
            "image_path": img_path
        })
        last_extracted_img = gray_small

    # メモリを節約（フレーム保存領域は不要になったので削除）
    frame_storage.clear()

    print(f"抽出完了: {len(scenes)} 枚のスライド画像を抽出しました")
    return scenes, task_temp_dir


def create_presentation(title: str, scenes: list, transcript: list, output_pptx_path: str):
    """
    抽出した画像と文字起こしテキストをマッピングし、PowerPointプレゼンテーションを生成する。
    transcript が空リストの場合は画像のみのスライドを生成する。
    
    Gemini APIキーが設定されている場合は、スライドごとに字幕をまとめて
    5行の要点 + メインメッセージを抽出し、スライドに追加する。
    """
    prs = Presentation()
    # スライドサイズを 16:9 ワイドスクリーンに設定
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    # 白紙スライドのレイアウト (blank layout is index 6)
    blank_slide_layout = prs.slide_layouts[6]

    # --- Gemini 初期化（オプション） ---
    summarizer = None
    #ty:
    #   summarizer = GeminiSummarizer()
    #  print("✓ Gemini API が有効です。スライド要約を生成します。")
    #except ValueError as e:
    #    print(f"ℹ Gemini API が設定されていません。テキストボックスには元の字幕を表示します。({e})")

    # --- 1. タイトルスライドの作成 ---
    slide = prs.slides.add_slide(blank_slide_layout)

    # タイトル用テキストボックス
    title_box = slide.shapes.add_textbox(Inches(1.0), Inches(2.2), Inches(11.333), Inches(3.0))
    tf = title_box.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(44)
    p.font.bold = True
    p.font.name = "Arial"
    p.font.color.rgb = RGBColor(33, 37, 41)

    p2 = tf.add_paragraph()
    p2.text = "YouTube動画から自動生成されたスライド資料"
    p2.font.size = Pt(20)
    p2.font.name = "Arial"
    p2.font.color.rgb = RGBColor(108, 117, 125)
    p2.space_before = Pt(20)

    # --- 2. コンテンツスライドの作成 ---
    has_transcript = bool(transcript)

    for i, scene in enumerate(scenes):
        current_time = scene["timestamp"]
        next_time = scenes[i + 1]["timestamp"] if i + 1 < len(scenes) else float('inf')

        slide = prs.slides.add_slide(blank_slide_layout)

        if has_transcript:
            # 左側: 画像（幅 5.8インチ）
            img_left = Inches(0.8)
            img_top = Inches(1.5)
            img_width = Inches(5.8)
            slide.shapes.add_picture(scene["image_path"], img_left, img_top, width=img_width)

            # このスライドの時間範囲に該当する字幕を結合
            slide_text_list = []
            for entry in transcript:
                start = entry["start"]
                if current_time <= start < next_time:
                    slide_text_list.append(entry["text"])
            slide_text = "\n".join(slide_text_list).strip()
            if not slide_text:
                slide_text = "(この区間の文字起こしデータはありません)"

            # 右側: テキストボックス
            text_box = slide.shapes.add_textbox(Inches(7.0), Inches(1.5), Inches(5.5), Inches(4.5))
            tf = text_box.text_frame
            tf.word_wrap = True

            minutes = int(current_time // 60)
            seconds = int(current_time % 60)
            p_time = tf.paragraphs[0]
            p_time.text = f"【シーン開始: {minutes:02d}:{seconds:02d}】"
            p_time.font.size = Pt(14)
            p_time.font.bold = True
            p_time.font.color.rgb = RGBColor(0, 123, 255)
            p_time.space_after = Pt(10)

            # === Gemini で要約を生成 ===
            """
            if summarizer and slide_text and "(この区間の文字起こしデータはありません)" not in slide_text:
                try:
                    summary_result = summarizer.summarize_slide_content(slide_text)
                    
                    # 【キーポイント】セクション
                    if summary_result.get("key_points"):
                        p_key_title = tf.add_paragraph()
                        p_key_title.text = "【要点】"
                        p_key_title.font.size = Pt(12)
                        p_key_title.font.bold = True
                        p_key_title.font.color.rgb = RGBColor(220, 53, 69)
                        p_key_title.space_before = Pt(8)
                        p_key_title.space_after = Pt(4)
                        
                        for key_point in summary_result["key_points"]:
                            p_kp = tf.add_paragraph()
                            p_kp.text = f"• {key_point}"
                            p_kp.font.size = Pt(11)
                            p_kp.font.name = "Arial"
                            p_kp.font.color.rgb = RGBColor(50, 50, 50)
                            p_kp.level = 0
                            p_kp.space_after = Pt(3)
                    
                    # 【メインメッセージ】セクション
                    if summary_result.get("main_message"):
                        p_main_title = tf.add_paragraph()
                        p_main_title.text = "💡 最も言いたいこと"
                        p_main_title.font.size = Pt(12)
                        p_main_title.font.bold = True
                        p_main_title.font.color.rgb = RGBColor(0, 102, 204)
                        p_main_title.space_before = Pt(8)
                        p_main_title.space_after = Pt(4)
                        
                        p_main = tf.add_paragraph()
                        p_main.text = summary_result["main_message"]
                        p_main.font.size = Pt(11)
                        p_main.font.name = "Arial"
                        p_main.font.color.rgb = RGBColor(20, 20, 100)
                        p_main.font.italic = True
                        p_main.line_spacing = 1.2
                        
                except Exception as e:
                    print(f"スライド {i+1} の要約生成に失敗: {e}")
                    # フォールバック: 元の字幕を表示
                    p_content = tf.add_paragraph()
                    p_content.text = slide_text
                    p_content.font.size = Pt(11)
                    p_content.font.name = "Arial"
                    p_content.font.color.rgb = RGBColor(50, 50, 50)
                    p_content.line_spacing = 1.3
            else:
                """
                # Geminiがない場合は元の字幕を表示
                p_content = tf.add_paragraph()
                p_content.text = slide_text
                p_content.font.size = Pt(11)
                p_content.font.name = "Arial"
                p_content.font.color.rgb = RGBColor(50, 50, 50)
                p_content.line_spacing = 1.3

        else:
            # 字幕なし: 画像をスライド全体に広げて配置
            img_left = Inches(0.8)
            img_top = Inches(0.8)
            img_width = Inches(11.733)
            slide.shapes.add_picture(scene["image_path"], img_left, img_top, width=img_width)

            # タイムスタンプのみ表示
            minutes = int(current_time // 60)
            seconds = int(current_time % 60)
            ts_box = slide.shapes.add_textbox(Inches(0.2), Inches(0.1), Inches(4.0), Inches(0.5))
            tf = ts_box.text_frame
            p = tf.paragraphs[0]
            p.text = f"{minutes:02d}:{seconds:02d}"
            p.font.size = Pt(12)
            p.font.color.rgb = RGBColor(150, 150, 150)

    prs.save(output_pptx_path)
    print(f"PowerPointファイルを保存しました: {output_pptx_path}")


def process_youtube_to_presentation(
    url: str,
    min_static_duration: float = 10.0,
    change_level: int = 5
) -> dict:
    """
    YouTube URL からプレゼンテーションを生成する一連の処理を実行する。
    字幕が取得できない場合は画像のみのスライドを生成する。

    Parameters
    ----------
    url : str
        YouTube 動画の URL。
    min_static_duration : float
        静止区間の最小継続時間（秒）。
    change_level : int
        変化検知の感度（1〜10）。1が最も敏感、10が最も鈍感。
    """
    video_id = extract_video_id(url)

    # 1. 字幕の取得（失敗しても処理続行）
    print("字幕の取得中...")
    transcript = get_transcript(url, video_id)
    if transcript:
        print(f"字幕を取得しました（{len(transcript)} エントリ）。")
    else:
        print("字幕なし。画像のみのスライドを生成します。")

    # 一時的な動画ファイルの保存パスを設定
    unique_id = str(uuid.uuid4())
    temp_video_path = os.path.join(TEMP_DIR, f"{unique_id}.mp4")

    try:
        # 2. 動画のダウンロード
        print("動画のダウンロード中...")
        title = download_video(url, temp_video_path)

        # 3. I フレームを参照した静止区間の検知と画像抽出
        print("静止区間の検知中（I フレームのみ参照）...")
        scenes, task_temp_dir = detect_static_scenes(
            temp_video_path,
            min_static_duration=min_static_duration,
            change_level=change_level
        )

        if not scenes:
            raise ValueError(
                "静止シーンが検出されませんでした。"
                "最小静止時間を短くするか、変化レベルを下げてみてください。"
            )

        # 4. プレゼンテーションファイルの生成
        # ファイル名は動画タイトルをベースに生成（特殊文字を除去）
        safe_title = sanitize_filename(title)
        output_filename = f"{safe_title}.pptx"
        output_pptx_path = os.path.join(task_temp_dir, output_filename)
        
        # 同じファイル名が既に存在する場合は、UUIDの一部を追加
        counter = 1
        base_name = output_filename.replace(".pptx", "")
        while os.path.exists(output_pptx_path):
            output_filename = f"{base_name}_{counter}.pptx"
            output_pptx_path = os.path.join(task_temp_dir, output_filename)
            counter += 1

        print("PowerPointの生成中...")
        create_presentation(title, scenes, transcript, output_pptx_path)

        # フロントエンドに返す結果データを整形
        formatted_scenes = []
        for i, scene in enumerate(scenes):
            current_time = scene["timestamp"]
            next_time = scenes[i + 1]["timestamp"] if i + 1 < len(scenes) else float('inf')

            # テキストの再抽出（プレビュー用）
            slide_text_list = []
            for entry in transcript:
                start = entry["start"]
                if current_time <= start < next_time:
                    slide_text_list.append(entry["text"])
            slide_text = " ".join(slide_text_list).strip()

            formatted_scenes.append({
                "id": i,
                "timestamp": current_time,
                "image_name": os.path.basename(scene["image_path"]),
                "text": slide_text or "(字幕なし)"
            })

        return {
            "success": True,
            "task_id": os.path.basename(task_temp_dir),
            "title": title,
            "pptx_filename": output_filename,
            "scenes": formatted_scenes,
            "has_transcript": bool(transcript),
        }

    finally:
        # ダウンロードした動画ファイル（容量が大きい）は不要になったので削除
        if os.path.exists(temp_video_path):
            try:
                os.remove(temp_video_path)
                print(f"一時動画ファイルを削除しました: {temp_video_path}")
            except Exception as e:
                print(f"一時動画ファイルの削除に失敗しました: {e}")
