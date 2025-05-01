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