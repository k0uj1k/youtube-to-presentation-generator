import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from starlette.background import BackgroundTask
from app.services.youtube_service import (
    process_youtube_to_presentation,
    cleanup_all_source_cache,
    cleanup_source_cache_for_task,
    TEMP_DIR,
)

# .env ファイルから環境変数を読み込む
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="YouTube to Presentation Generator API")

# リクエストスキーマ
class GenerateRequest(BaseModel):
    url: str
    change_level: int = 5  # 変化検知レベル（1=最敏感 〜 10=最鈍感）
    comparison_resolution: str = "160x90"
    ai_summary_enabled: bool = False

# 静的画像配信用エンドポイント
@app.get("/api/images/{task_id}/{image_name}")
def get_extracted_image(task_id: str, image_name: str):
    """
    生成タスクで抽出された画像を返す。
    """
    # ディレクトリトラバーサル防止のため、ファイル名とパスを厳密にチェック
    safe_task_id = os.path.basename(task_id)
    safe_image_name = os.path.basename(image_name)
    image_path = os.path.join(TEMP_DIR, safe_task_id, safe_image_name)
    
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="画像が見つかりません。")
        
    return FileResponse(image_path)

# PPTXダウンロード用エンドポイント
@app.get("/api/download/{task_id}/{filename}")
def download_presentation(task_id: str, filename: str):
    """
    生成されたPowerPointファイルをダウンロードする。
    """
    safe_task_id = os.path.basename(task_id)
    safe_filename = os.path.basename(filename)
    pptx_path = os.path.join(TEMP_DIR, safe_task_id, safe_filename)
    
    if not os.path.exists(pptx_path):
        raise HTTPException(status_code=404, detail="プレゼンテーションファイルが見つかりません。")
        
    return FileResponse(
        pptx_path, 
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=safe_filename,
        background=BackgroundTask(cleanup_source_cache_for_task, safe_task_id)
    )

# プレゼンテーション生成API
@app.post("/api/generate")
def generate_presentation_api(req: GenerateRequest):
    """
    YouTube URL からプレゼンテーションを生成し、スライド情報とダウンロードURLを返す。
    """
    try:
        result = process_youtube_to_presentation(
            url=req.url,
            change_level=req.change_level,
            comparison_resolution=req.comparison_resolution,
            ai_summary_enabled=req.ai_summary_enabled
        )
        return result
    except ValueError as ve:
        # ユーザーの入力エラー（字幕なし、URLエラーなど）
        error_msg = str(ve)
        # ユーザーフレンドリーなメッセージに変換
        user_friendly_msg = _translate_error(error_msg)
        raise HTTPException(status_code=400, detail=user_friendly_msg)
    except Exception as e:
        # サーバー内部エラー
        import traceback
        print(f"ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="処理中に予期しないエラーが発生しました。ログを確認してください。")


@app.post("/api/source-cache/clear")
def clear_source_cache_api():
    """
    保持中の動画・字幕ソースキャッシュをすべて削除する。
    """
    try:
        cleanup_all_source_cache()
        return {"success": True}
    except Exception as e:
        import traceback
        print(f"ERROR: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"ソースキャッシュの削除に失敗しました: {e}")


def _translate_error(error_msg: str) -> str:
    """エラーメッセージを日本語に翻訳（既に日本語の場合もある）"""
    translations = {
        "Video unavailable": "指定された動画は存在しないか、非公開、または地域制限によりアクセスできません。",
        "HTTP Error 404": "動画が見つかりません。URLが正しいか確認してください。",
        "HTTP Error 403": "動画にアクセスできません。地域制限やアクセス権限の問題の可能性があります。",
        "No data available": "動画データの取得に失敗しました。",
    }
    
    for eng_key, ja_value in translations.items():
        if eng_key.lower() in error_msg.lower():
            return ja_value
    
    # 既に日本語なら返す、そうでなければ一般的なメッセージ
    return error_msg if "。" in error_msg or "、" in error_msg else f"エラーが発生しました: {error_msg}"

# フロントエンド静的ファイルの配信
# 静的ディレクトリを作成
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# 静的ファイルをマウント（APIエンドポイントの後ろでマウントする必要がある）
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
