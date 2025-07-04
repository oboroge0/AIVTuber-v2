from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)

class SystemPromptLoader:
    @staticmethod
    def load(prompt_path: str) -> str:
        """システムプロンプトを読み込む"""
        try:
            with open(Path("prompts") / prompt_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"システムプロンプトの読み込みエラー: {e}")
            return "" 