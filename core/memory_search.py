"""
メモリ検索モジュール
"""
import os
import json
from typing import List, Dict, Any
from datetime import datetime
from .models import MemoryItem
from utils.logger import get_logger
from core.config import Config

logger = get_logger(__name__)

class MemorySearcher:
    """メモリ検索クラス"""
    
    def __init__(self):
        """初期化"""
        self.hipporag_dir = Config.HIPPORAG_DIR
        if not os.path.exists(self.hipporag_dir):
            os.makedirs(self.hipporag_dir)
        
        # メモリファイルのパス
        self.memory_file = os.path.join(self.hipporag_dir, "memories.json")
        
        # メモリの読み込み
        self.memories = self._load_memories()
    
    def _load_memories(self) -> Dict[str, Any]:
        """
        メモリを読み込む
        
        Returns:
            Dict[str, Any]: メモリデータ
        """
        if not os.path.exists(self.memory_file):
            return {
                "triples": [],
                "last_updated": datetime.now().isoformat()
            }
        
        try:
            with open(self.memory_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading memories: {e}")
            return {
                "triples": [],
                "last_updated": datetime.now().isoformat()
            }
    
    def _save_memories(self) -> None:
        """メモリを保存する"""
        try:
            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error saving memories: {e}")
    
    def _calculate_similarity(self, query: str, text: str) -> float:
        """
        テキストの類似度を計算する
        
        Args:
            query: クエリテキスト
            text: 比較するテキスト
            
        Returns:
            float: 類似度（0-1）
        """
        # 単語の重複をカウント
        query_words = set(query.lower().split())
        text_words = set(text.lower().split())
        
        # Jaccard類似度を計算
        intersection = len(query_words & text_words)
        union = len(query_words | text_words)
        
        return intersection / union if union > 0 else 0.0
    
    def search_memory(self, query: str, top_k: int = 5) -> List[MemoryItem]:
        """
        メモリを検索する
        
        Args:
            query: 検索クエリ
            top_k: 取得する件数
            
        Returns:
            List[MemoryItem]: メモリアイテムのリスト
        """
        try:
            # 各メモリのスコアを計算
            scored_memories = []
            for triple in self.memories["triples"]:
                score = self._calculate_similarity(query, triple["text"])
                scored_memories.append(MemoryItem(
                    triple=triple["triple"],
                    text=triple["text"],
                    score=score
                ))
            
            # スコアでソート
            scored_memories.sort(key=lambda x: x.score, reverse=True)
            
            # 上位k件を返す
            return scored_memories[:top_k]
            
        except Exception as e:
            logger.error(f"Error searching memory: {e}")
            return []
    
    def add_memory(self, triple: str, text: str) -> None:
        """
        メモリを追加する
        
        Args:
            triple: トリプル
            text: テキスト
        """
        try:
            # 新しいメモリを追加
            self.memories["triples"].append({
                "triple": triple,
                "text": text,
                "timestamp": datetime.now().isoformat()
            })
            
            # メモリを保存
            self._save_memories()
            
        except Exception as e:
            logger.error(f"Error adding memory: {e}")
    
    def clear_memories(self) -> None:
        """メモリをクリアする"""
        try:
            self.memories = {
                "triples": [],
                "last_updated": datetime.now().isoformat()
            }
            self._save_memories()
        except Exception as e:
            logger.error(f"Error clearing memories: {e}") 