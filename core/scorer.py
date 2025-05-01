"""
コメントスコアラーモジュール
"""
from typing import List
from .models import Comment
from utils.logger import get_logger

logger = get_logger(__name__)

class CommentScorer:
    """コメントスコアラー"""
    
    def score_comment(self, comment: Comment) -> float:
        """
        コメントにスコアを付ける
        
        Args:
            comment: コメントデータ
            
        Returns:
            float: スコア（0.0-1.0）
        """
        score = 0.0
        text = comment.text.lower()
        
        # コメントの長さによるスコア
        if 10 <= len(text) <= 100:
            score += 0.3
        
        # 質問形式のボーナス
        if '?' in text or '？' in text:
            score += 0.2
        
        # 特定のキーワードによるボーナス
        keywords = ['好き', 'かわいい', 'かっこいい', 'すごい', '面白い', '笑', 'www', '草']
        for keyword in keywords:
            if keyword in text:
                score += 0.1
        
        # スコアの上限を1.0に制限
        return min(score, 1.0) 