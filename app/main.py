import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.services.youtube_service import process_youtube_to_presentation, TEMP_DIR

app = FastAPI(title="YouTube to Presentation Generator API")

# リクエストスキーマ
class GenerateRequest(BaseModel):
    url: str
    min_static_duration: float = 10.0
    change_level: int = 5  # 変化検知レベル（1=最敏感 〜 10=最鈍感）

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
        filename=safe_filename
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
            min_static_duration=req.min_static_duration,
            change_level=req.change_level
        )
        return result
    except ValueError as ve:
        # ユーザーの入力エラー（字幕なし、URLエラーなど）
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # サーバー内部エラー
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"処理中にエラーが発生しました: {str(e)}")

# フロントエンド静的ファイルの配信
# 静的ディレクトリを作成
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
os.makedirs(STATIC_DIR, exist_ok=True)

# 静的ファイルをマウント（APIエンドポイントの後ろでマウントする必要がある）
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
