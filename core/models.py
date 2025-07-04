"""
データモデルモジュール
"""
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Comment:
    """コメントデータクラス"""
    id: str
    author: str
    text: str
    timestamp: datetime
    source: str = "youtube"  # "youtube" or "voice"
    priority: str = "normal"  # "normal" or "high"
    is_voice_input: bool = False
    is_super_chat: bool = False
    is_member: bool = False

@dataclass
class MemoryItem:
    """メモリアイテムデータクラス"""
    triple: str
    text: str
    score: float

@dataclass
class Video:
    """動画データクラス"""
    id: str
    title: str
    startTime: datetime 