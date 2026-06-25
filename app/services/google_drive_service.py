import os
import json
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

class GoogleDriveService:
    """Google ドライブへプレゼンテーションファイルをアップロードし、
    Google スライドに自動変換して共有・閲覧URLを取得するサービス。
    """
    
    def __init__(self):
        self.creds = self._load_credentials()
        self.drive_service = build('drive', 'v3', credentials=self.creds) if self.creds else None

    def _load_credentials(self):
        """環境変数 GOOGLE_SERVICE_ACCOUNT_JSON からサービスアカウントの資格情報をロードする。"""
        cred_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not cred_json:
            return None

        try:
            # 1. 文字列（JSON形式）としてパースを試みる
            info = json.loads(cred_json)
            return service_account.Credentials.from_service_account_info(
                info,
                scopes=['https://www.googleapis.com/auth/drive']
            )
        except json.JSONDecodeError:
            # 2. JSONファイルへの絶対パスと仮定して読み込む
            if os.path.exists(cred_json):
                return service_account.Credentials.from_service_account_file(
                    cred_json,
                    scopes=['https://www.googleapis.com/auth/drive']
                )
        except Exception as e:
            print(f"Google 認証情報のロードに失敗しました: {e}")
        return None

    def upload_and_convert_to_slides(self, local_file_path: str, filename: str) -> str:
        """ローカルの PowerPoint (.pptx) ファイルを Google ドライブにアップロードし、
        Google スライドに自動変換し、共有（リンクを知っている全員が閲覧可能）を設定してリンクURLを返す。
        """
        if not self.drive_service:
            raise ValueError(
                "Google ドライブ連携がセットアップされていません。.env ファイルに "
                "GOOGLE_SERVICE_ACCOUNT_JSON を正しく設定してください。"
            )

        if not os.path.exists(local_file_path):
            raise FileNotFoundError(f"アップロード対象のファイルが見つかりません: {local_file_path}")

        try:
            # 1. アップロードメタデータの設定（Google スライドへの変換を指定）
            file_metadata = {
                'name': filename.replace('.pptx', ''),
                'mimeType': 'application/vnd.google-apps.presentation'  # Google スライドの MIME タイプ
            }
            
            media = MediaFileUpload(
                local_file_path,
                mimetype='application/vnd.openxmlformats-officedocument.presentationml.presentation',
                resumable=True
            )
            
            # 2. アップロードの実行
            print(f"Google ドライブへアップロード・スライド変換中: {filename}")
            uploaded_file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink'
            ).execute()
            
            file_id = uploaded_file.get('id')
            web_view_link = uploaded_file.get('webViewLink')
            
            if not file_id:
                raise RuntimeError("アップロードされたファイルの ID を取得できませんでした。")
                
            # 3. 共有設定（リンクを知っている全員に閲覧権限を付与）
            print(f"共有権限を設定中... ファイルID: {file_id}")
            permission_body = {
                'role': 'reader',
                'type': 'anyone'
            }
            self.drive_service.permissions().create(
                fileId=file_id,
                body=permission_body
            ).execute()
            
            # 再度共有設定が反映された webViewLink を取得
            file_info = self.drive_service.files().get(
                fileId=file_id,
                fields='webViewLink'
            ).execute()
            
            return file_info.get('webViewLink', web_view_link)

        except Exception as e:
            raise RuntimeError(f"Google ドライブへのアップロードまたはスライド変換に失敗しました: {e}")
