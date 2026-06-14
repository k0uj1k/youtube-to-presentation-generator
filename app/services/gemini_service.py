"""
Gemini APIを使用したスライド字幕テキストの要約・抽出サービス
"""

import os
# Use the new google.genai package; fall back to deprecated one if unavailable
try:
    import google.genai as genai
except ImportError:
    import google.generativeai as genai


class GeminiSummarizer:
    """
    Gemini APIを使用してテキストをまとめるクラス
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Gemini APIを初期化する。
        
        Parameters
        ----------
        api_key : str, optional
            Gemini API キー。指定されない場合は GEMINI_API_KEY 環境変数から取得。
        
        Raises
        ------
        ValueError
            API キーが指定されていない場合。
        """
        if api_key is None:
            api_key = os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError(
                "Gemini API キーが設定されていません。"
                "GEMINI_API_KEY 環境変数を設定するか、"
                "GeminiSummarizer(api_key='your-key') で指定してください。"
            )
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.5-flash-lite")

    def summarize_slide_content(self, slide_text: str) -> Dict[str, any]:
        """
        スライドのテキストを要約する。
        5行の要点 + このスライドで最も言いたいことを抽出。
        
        Parameters
        ----------
        slide_text : str
            スライドの字幕テキスト（複数行の可能性あり）
        
        Returns
        -------
        dict
            以下のキーを持つ辞書：
            - "key_points": list[str] - 5行の要点リスト（最大5個）
            - "main_message": str - このスライドで最も言いたいこと
            - "error": str (optional) - エラーが発生した場合のメッセージ
        
        Examples
        --------
        >>> summarizer = GeminiSummarizer()
        >>> result = summarizer.summarize_slide_content("このスライドの内容...")
        >>> print(result["main_message"])
        """
        # &g&t を改行に変換してテキストを正規化
        # slide_text = slide_text.replace("&gt;&gt;", " ")
        if not slide_text or not slide_text.strip():
            return {
                "key_points": [],
                "main_message": "(内容なし)"
            }

        prompt = f"""以下のスライドの字幕テキストを分析してください。

【指示】
1. このスライドの内容から、**5行までの主要なポイント**を箇条書きで抽出してください。
2. その後、**このスライドで最も言いたいことが何か（メインメッセージ）を1行で簡潔に述べてください。

【テキスト】
{slide_text}

【出力形式】
以下の形式で出力してください（Markdownは使わない、プレーンテキストのみ）：

KEY_POINTS:
- 
- 
-
-
-
...

MAIN_MESSAGE: このスライドで最も言いたいことをここに書いてください。"""

        try:
            response = self.model.generate_content(prompt)
            
            # 応答テキストをパース
            response_text = response.text.strip()
            
            # KEY_POINTS セクションを抽出
            key_points = []
            if "KEY_POINTS:" in response_text:
                # KEY_POINTS: から MAIN_MESSAGE: までの間を抽出
                kp_start = response_text.find("KEY_POINTS:") + len("KEY_POINTS:")
                mm_start = response_text.find("MAIN_MESSAGE:")
                
                if mm_start == -1:
                    mm_start = len(response_text)
                
                kp_section = response_text[kp_start:mm_start].strip()
                
                # "- ポイント" という行を抽出
                for line in kp_section.split("\n"):
                    line = line.strip()
                    if line.startswith("- "):
                        key_points.append(line[2:].strip())
                    elif line and not line.startswith("- "):
                        # "- " がない場合でも内容があれば追加
                        if line:
                            key_points.append(line)
            
            # MAIN_MESSAGE を抽出
            main_message = ""
            if "MAIN_MESSAGE:" in response_text:
                mm_start = response_text.find("MAIN_MESSAGE:") + len("MAIN_MESSAGE:")
                main_message = response_text[mm_start:].strip()
                # 最初の1行のみ取得（複数行の場合）
                main_message = main_message.split("\n")[0].strip()
            
            return {
                "key_points": key_points[:5],  # 最大5個に制限
                "main_message": main_message or "(内容を自動生成できませんでした)"
            }

        except Exception as e:
            print(f"Gemini API エラー: {e}")
            return {
                "key_points": [],
                "main_message": "(要約の生成に失敗しました)",
                "error": str(e)
            }


def get_summarizer() -> GeminiSummarizer:
    """
    グローバルな GeminiSummarizer インスタンスを取得する。
    
    Returns
    -------
    GeminiSummarizer
        初期化済みの GeminiSummarizer インスタンス
    
    Raises
    ------
    ValueError
        API キーが設定されていない場合
    """
    return GeminiSummarizer()
