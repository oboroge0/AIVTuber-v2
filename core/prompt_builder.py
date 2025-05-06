"""
プロンプトビルダーモジュール
"""
from core.system_prompt_loader import SystemPromptLoader
from utils.logger import get_logger
from memory.hipporag_memory import VTuberMemory
from typing import Optional

logger = get_logger(__name__)

class PromptBuilder:
    """プロンプトビルダー"""
    
    def __init__(self, history_mgr, memory: VTuberMemory):
        self.history_mgr = history_mgr
        self.memory = memory

    def build(self, *, comment: str, current_theme: Optional[str] = None) -> str:
        """
        構造化されたプロンプトを構築する
        
        Args:
            comment: コメント
            current_theme: 現在の配信テーマ
            
        Returns:
            str: 構築されたプロンプト
        """
        # 関連する記憶を検索
        retrieved = self.memory.retrieve(comment)
        rag_memory = "\n".join([f"【記憶{i+1}】{c}" for i, c in enumerate(retrieved)])
        
        recent_history = self.history_mgr.get_last_n_turns(10)

        prompt = f"""
<memory>
{rag_memory}
</memory>

<recent>
{recent_history}
</recent>

<theme>
現在の配信テーマ: {current_theme if current_theme else "未設定"}
</theme>

<user>
{comment}
</user>""" 

        return prompt
