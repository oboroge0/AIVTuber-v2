"""
プロンプトビルダーモジュール
"""
from core.system_prompt_loader import SystemPromptLoader
from utils.logger import get_logger

logger = get_logger(__name__)

class PromptBuilder:
    """プロンプトビルダー"""
    
    def __init__(self, history_mgr, system_prompt_path="comment_mode.txt"):
        self.history_mgr = history_mgr
        self.system_prompt = SystemPromptLoader.load(system_prompt_path)

    def build(self, *, comment: str, rag_memory: str) -> str:
        """
        構造化されたプロンプトを構築する
        
        Args:
            comment: コメント
            rag_memory: RAGメモリの内容
            
        Returns:
            str: 構築されたプロンプト
        """
        recent_history = self.history_mgr.get_last_n_turns(10)

        prompt = f"""<system>
{self.system_prompt}
</system>

<memory>
{rag_memory}
</memory>

<recent>
{recent_history}
</recent>

<user>
{comment}
</user>""" 

        logger.info(f"構築されたプロンプト: {prompt}")

        return prompt
