import threading
from typing import Dict, List, Optional, Any

class TaskCancelledException(Exception):
    """タスクがユーザーによってキャンセルされたことを示す例外"""
    pass

class TaskState:
    """非同期タスクの実行状態を保持するクラス"""
    def __init__(self):
        self.status: str = "processing"  # 状態: "processing", "completed", "failed", "cancelled"
        self.progress: int = 0          # 進捗率 (0〜100)
        self.logs: List[str] = []       # 処理ログのリスト
        self.detail: str = ""           # 現在の処理詳細
        self.result: Optional[dict] = None  # 完了時の実行結果
        self.error: Optional[str] = None    # エラー発生時のエラーメッセージ
        self.cancel_event = threading.Event()  # 中止用イベント

    def log(self, message: str, progress: Optional[int] = None):
        """ログを記録し、進捗率を更新する。キャンセルされている場合は例外を投げる"""
        if self.cancel_event.is_set():
            self.status = "cancelled"
            raise TaskCancelledException("タスクがユーザーによって中止されました。")
            
        self.logs.append(message)
        self.detail = message
        if progress is not None:
            self.progress = max(0, min(100, progress))
        print(f"[TaskLog] {message} (進捗: {self.progress}%)")

    def check_cancelled(self):
        """キャンセルが要求されているかチェックし、要求されていれば例外を投げる"""
        if self.cancel_event.is_set():
            self.status = "cancelled"
            raise TaskCancelledException("タスクがユーザーによって中止されました。")

# グローバルなタスク状態管理用の辞書 (task_id -> TaskState)
tasks: Dict[str, TaskState] = {}
