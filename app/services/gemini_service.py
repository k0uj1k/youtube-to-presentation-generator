"""
Gemini APIを使用したスライド字幕テキストの要約・抽出サービス
"""

import os
from typing import Any, Dict, Optional

# New Google Gemini SDK
from google import genai

# Deprecated SDK の FutureWarning を抑制
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)


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
        
        # 新 SDK クライアントの初期化
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash-lite"

    def summarize_slide_content(self, slide_text: str) -> Dict[str, Any]:
        """スライドの字幕テキストを要約し、主要ポイントとメインメッセージを抽出します。

        Parameters
        ----------
        slide_text: str
            スライドの字幕テキスト。

        Returns
        -------
        Dict[str, Any]
            key_points（最大5項目）と main_message を含む辞書。
        """
        prompt = f"""以下のスライドの字幕テキストを分析してください。

【指示】
1. このスライドの内容から、**5行までの主要なポイント**を箇条書きで抽出してください。
2. その後、**このスライドで最も言いたいことが何か（メインメッセージ）を1行で簡潔に述べてください**。

【テキスト】
{slide_text}

【出力形式】
以下の形式で出力してください（Markdownは使わない、プレーンテキストのみ）:

KEY_POINTS:
- 
- 
- 
- 
- 
...

MAIN_MESSAGE: このスライドで最も言いたいことをここに書いてください。
"""
        import time
        max_retries = 3
        backoff = 10.0

        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                response_text = response.text.strip()

                # KEY_POINTS 抽出
                key_points = []
                if "KEY_POINTS:" in response_text:
                    kp_start = response_text.find("KEY_POINTS:") + len("KEY_POINTS:")
                    mm_start = response_text.find("MAIN_MESSAGE:")
                    if mm_start == -1:
                        mm_start = len(response_text)
                    kp_section = response_text[kp_start:mm_start].strip()
                    for line in kp_section.split("\n"):
                        line = line.strip()
                        if line.startswith("- "):
                            key_points.append(line[2:].strip())
                        elif line:
                            key_points.append(line)

                # MAIN_MESSAGE 抽出
                main_message = ""
                if "MAIN_MESSAGE:" in response_text:
                    mm_start = response_text.find("MAIN_MESSAGE:") + len("MAIN_MESSAGE:")
                    main_message = response_text[mm_start:].strip().split("\n")[0].strip()

                return {
                    "key_points": key_points[:5],
                    "main_message": main_message or "(内容を自動生成できませんでした)"
                }
            except Exception as e:
                print(f"Gemini API エラー (試行 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    time.sleep(backoff)
                    backoff *= 2
                else:
                    raise e

def get_summarizer() -> GeminiSummarizer:
    """グローバルな GeminiSummarizer インスタンスを取得する。

    Returns
    -------
    GeminiSummarizer
        初期化済みの GeminiSummarizer インスタンス
    """
    return GeminiSummarizer()
