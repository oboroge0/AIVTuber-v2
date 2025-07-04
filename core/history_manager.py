from collections import deque
from pathlib import Path
import json, datetime
from utils.helpers import create_backup
from utils.logger import get_logger

logger = get_logger(__name__)

class HistoryManager:
    """Store recent dialogue turns in memory and disk."""

    def __init__(self, max_turns: int = 1000, persist_dir: Path | None = None, backup_dir: Path | None = None):
        self.turns = deque(maxlen=max_turns)
        self.persist_dir = persist_dir
        self.backup_dir = backup_dir
        self.backup_counter = 0
        self.backup_interval = 10  # 10回の会話ごとにバックアップ
        
        if persist_dir:
            persist_dir.mkdir(parents=True, exist_ok=True)
            self.history_file = persist_dir / "chat_history.json"
            self._load_history()

    def _load_history(self):
        """履歴を読み込む"""
        if self.history_file.exists():
            try:
                with self.history_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.turns = deque(data.get("turns", []), maxlen=self.turns.maxlen)
                    self.backup_counter = len(self.turns) % self.backup_interval
            except Exception as e:
                logger.error(f"Error loading history: {e}")

    def _save_history(self):
        """履歴を保存する"""
        if self.persist_dir:
            try:
                with self.history_file.open("w", encoding="utf-8") as f:
                    json.dump({"turns": list(self.turns)}, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.error(f"Error saving history: {e}")

    def _create_backup(self):
        """バックアップを作成する"""
        if self.backup_dir and self.history_file.exists():
            try:
                create_backup(str(self.history_file), str(self.backup_dir))
                logger.info("History backup created")
            except Exception as e:
                logger.error(f"Error creating backup: {e}")

    def append(self, role: str, text: str):
        """会話を追加"""
        self.turns.append({"role": role, "text": text, "ts": datetime.datetime.now().isoformat()})
        self._save_history()
        
        # バックアップカウンターを更新
        self.backup_counter = (self.backup_counter + 1) % self.backup_interval
        if self.backup_counter == 0:
            self._create_backup()

    def get_last_n_turns(self, n: int = 10) -> str:
        """Return the last *n* turns as a newline‑joined string: 'user: ...' """
        selected = list(self.turns)[-n:]
        return "\n".join(f"{t['role']}: {t['text']}" for t in selected) 