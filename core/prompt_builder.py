"""
プロンプトビルダーモジュール
"""
from typing import List
from .models import MemoryItem
from utils.logger import get_logger

logger = get_logger(__name__)

class PromptBuilder:
    """プロンプトビルダー"""
    
    def build_prompt(self, comment: str, memory: List[MemoryItem], history: List[str]) -> str:
        """
        プロンプトを構築する
        
        Args:
            comment: コメント
            memory: メモリアイテムのリスト
            history: 会話履歴
            
        Returns:
            str: 構築されたプロンプト
        """
        # メモリの情報を追加
        memory_text = "\n".join([
            f"Memory {i+1}: {item.text} (Score: {item.score})"
            for i, item in enumerate(memory)
        ])
        
        # 会話履歴を追加
        history_text = "\n".join([
            f"Turn {i+1}: {turn}"
            for i, turn in enumerate(history[-5:])  # 直近5ターン
        ])
        
        # プロンプトを構築
        prompt = f"""
You are a friendly and engaging VTuber. Respond to the following comment in a natural and entertaining way.

Recent Memory:
{memory_text}

Conversation History:
{history_text}

Current Comment:
{comment}

Please respond in a way that:
1. Is natural and conversational
2. Shows personality
3. References relevant memories when appropriate
4. Maintains context from the conversation history
5. Is engaging and entertaining

Response:
"""
        return prompt.strip() 