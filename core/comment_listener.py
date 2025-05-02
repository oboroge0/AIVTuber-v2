"""
コメントリスナーモジュール
"""
import asyncio
from typing import Optional
from datetime import datetime, timezone
import pytchat

from .models import Comment
from utils.logger import get_logger

logger = get_logger(__name__)

class CommentListener:
    """YouTubeコメントリスナー"""
    
    def __init__(self, video_id: str, comment_queue: asyncio.Queue):
        """
        初期化
        
        Args:
            video_id: 動画ID
            comment_queue: コメントキュー
        """
        self._running = False
        self._comment_queue = comment_queue
        self._video_id = video_id
        self._chat = None
    
    async def start(self) -> None:
        """
        コメント監視を開始する
        """
        self._running = True
        
        try:
            # pytchatでコメント取得を開始
            self._chat = pytchat.create(self._video_id)
            
            # コメント監視タスクを開始
            asyncio.create_task(self._listen_comments())
            logger.info(f"コメント監視を開始しました: {self._video_id}")
            
        except Exception as e:
            logger.error(f"コメント監視開始エラー: {e}")
            self._running = False
    
    async def stop(self) -> None:
        """コメント監視を停止する"""
        self._running = False
        logger.info("コメント監視を停止しました")
    
    async def _listen_comments(self) -> None:
        """コメントを監視する"""
        while self._running:
            try:
                if not self._chat or not self._chat.is_alive():
                    logger.error("チャットが開始されていません")
                    await asyncio.sleep(5)
                    continue
                
                for c in self._chat.get().sync_items():
                    try:
                        # タイムスタンプを安全に処理
                        timestamp = datetime.now(timezone.utc)  # デフォルト値
                        if hasattr(c, 'timestamp'):
                            try:
                                timestamp = datetime.fromtimestamp(c.timestamp, timezone.utc)
                            except (ValueError, OSError):
                                pass  # 無効なタイムスタンプの場合は現在時刻を使用
                        
                        comment = Comment(
                            id=c.id,
                            author=c.author.name,
                            text=c.message,
                            timestamp=timestamp
                        )
                        # キューに追加（Producer）
                        await self._comment_queue.put(comment)
                        logger.info(f"Queued comment: {comment.author}: {comment.text}")
                    except Exception as e:
                        logger.error(f"コメント処理エラー: {e}")
                
                # ポーリング間隔
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"コメント監視エラー: {e}")
                await asyncio.sleep(5) 