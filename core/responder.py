"""
レスポンダーモジュール
"""
from openai import AsyncOpenAI
from utils.logger import get_logger
from core.config import Config
from core.system_prompt_loader import SystemPromptLoader

logger = get_logger(__name__)

class Responder:
    """レスポンダー"""
    
    def __init__(self, system_prompt_path="comment_mode.txt"):
        """初期化"""
        self.client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)
        self.system_prompt = SystemPromptLoader.load(system_prompt_path)
    
    async def generate_response(self, prompt: str) -> str:
        """
        レスポンスを生成する
        
        Args:
            prompt: プロンプト
            
        Returns:
            str: 生成されたレスポンス
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=1,
                max_tokens=300
            )

            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "申し訳ありません。応答の生成中にエラーが発生しました。おぼろげを呼んでください！"