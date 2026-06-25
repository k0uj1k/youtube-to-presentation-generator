import os
import threading
import uuid
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from app.services.youtube_service import process_youtube_to_presentation, TEMP_DIR
from app.services.task_manager import tasks, TaskState, TaskCancelledException

# .env ファイルから環境変数を読み込む
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="YouTube to Presentation Generator API")

# リクエストスキーマ
class GenerateRequest(BaseModel):
    url: str
    change_level: int = 5  # 変化検知レベル（1=最敏感 〜 10=最鈍感）
    ai_summary_enabled: bool = False
    save_format: str = "pptx"

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

def cleanup_temp_dir(exclude_video_id: str):
    """
    指定された動画ID以外の古い動画ファイルや一時タスクディレクトリを削除する。
    """
    if not os.path.exists(TEMP_DIR):
        return
    import shutil
    print(f"[CLEANUP] クリーンアップを開始します (除外対象動画ID: {exclude_video_id})")
    for name in os.listdir(TEMP_DIR):
        path = os.path.join(TEMP_DIR, name)
        # 動画ファイルの削除判定
        if name.startswith("video_") and name.endswith(".mp4"):
            if name != f"video_{exclude_video_id}.mp4":
                try:
                    os.remove(path)
                    print(f"[CLEANUP] 他の動画ファイルを削除しました: {name}")
                except Exception as e:
                    print(f"[CLEANUP] 動画ファイルの削除に失敗: {e}")
        # タスクディレクトリの削除判定
        elif os.path.isdir(path):
            try:
                shutil.rmtree(path)
                print(f"[CLEANUP] 古いタスクディレクトリを削除しました: {name}")
            except Exception as e:
                print(f"[CLEANUP] タスクディレクトリの削除に失敗: {e}")


@app.on_event("shutdown")
def shutdown_event():
    print("[SHUTDOWN] アプリケーションを終了します。一時データを全削除中...")
    if os.path.exists(TEMP_DIR):
        import shutil
        for name in os.listdir(TEMP_DIR):
            path = os.path.join(TEMP_DIR, name)
            try:
                if os.path.isdir(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                print(f"[SHUTDOWN] 削除しました: {name}")
            except Exception as e:
                print(f"[SHUTDOWN] 削除に失敗 {path}: {e}")

def _run_generation_task(task_id: str, url: str, change_level: int, ai_summary_enabled: bool, save_format: str):
    """バックグラウンドでプレゼンテーション生成を実行するスレッド用関数"""
    task_state = tasks.get(task_id)
    if not task_state:
        return
        
    try:
        result = process_youtube_to_presentation(
            url=url,
            change_level=change_level,
            ai_summary_enabled=ai_summary_enabled,
            save_format=save_format,
            task_state=task_state
        )
        task_state.result = result
        task_state.status = "completed"
    except TaskCancelledException as tce:
        task_state.status = "cancelled"
        task_state.error = str(tce)
    except ValueError as ve:
        # ユーザーの入力エラー（字幕なし、URLエラーなど）
        error_msg = str(ve)
        user_friendly_msg = _translate_error(error_msg)
        task_state.status = "failed"
        task_state.error = user_friendly_msg
    except Exception as e:
        # サーバー内部エラー
        import traceback
        print(f"ERROR in task {task_id}: {traceback.format_exc()}")
        task_state.status = "failed"
        task_state.error = "処理中に予期しないエラーが発生しました。サーバーのログを確認してください。"


# プレゼンテーション生成API
@app.post("/api/generate")
def generate_presentation_api(req: GenerateRequest):
    """
    YouTube URL からプレゼンテーションを生成する非同期タスクを開始し、タスクIDを返す。
    """
    try:
        # 新しいURL（動画ID）が指定された時点で、古い動画やタスクデータをクリーンアップ（URL更新時）
        from app.services.youtube_service import extract_video_id
        video_id = extract_video_id(req.url)
        cleanup_temp_dir(exclude_video_id=video_id)
    except Exception as e:
        print(f"[CLEANUP ERROR] {e}")

    task_id = str(uuid.uuid4())
    task_state = TaskState()
    tasks[task_id] = task_state
    
    # バックグラウンドスレッドを開始して非同期に処理を実行
    t = threading.Thread(
        target=_run_generation_task,
        args=(task_id, req.url, req.change_level, req.ai_summary_enabled, req.save_format),
        daemon=True
    )
    t.start()
    
    return {"task_id": task_id}


# タスクステータス取得API
@app.get("/api/status/{task_id}")
def get_task_status(task_id: str):
    """
    指定されたタスクの進捗率、ログ、エラーメッセージ、結果などを取得する。
    """
    task_state = tasks.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません。")
        
    return {
        "status": task_state.status,
        "progress": task_state.progress,
        "logs": task_state.logs,
        "detail": task_state.detail,
        "result": task_state.result,
        "error": task_state.error
    }


# タスクキャンセルAPI
@app.post("/api/cancel/{task_id}")
def cancel_task(task_id: str):
    """
    実行中のタスクを中止する。
    """
    task_state = tasks.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません。")
        
    task_state.cancel_event.set()
    task_state.confirm_response = "abort"
    task_state.confirm_event.set()
    task_state.status = "cancelled"
    return {"success": True}


# ユーザーの確認アクションを受け取るAPI
@app.post("/api/confirm/{task_id}/{action}")
def confirm_task(task_id: str, action: str):
    """
    スライド数超過時の一時停止に対するユーザーの確認アクションを受け取る。
    """
    task_state = tasks.get(task_id)
    if not task_state:
        raise HTTPException(status_code=404, detail="指定されたタスクが見つかりません。")
        
    if action not in ["abort", "continue"]:
        raise HTTPException(status_code=400, detail="無効なアクションです。")
        
    task_state.confirm_response = action
    task_state.confirm_event.set()
    return {"success": True}



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
