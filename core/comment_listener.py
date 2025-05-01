"""
コメントリスナーモジュール
"""
import asyncio
import json
from typing import Optional
from datetime import datetime, timezone
import pytchat

from .models import Comment
from utils.logger import get_logger

logger = get_logger(__name__)

class CommentListener:
    """YouTubeコメントリスナー"""
    
    def __init__(self):
        """
        初期化
        """
        self._running = False
        self._comment_queue = asyncio.Queue()
        self._current_video_id = None
        self._chat = None
    
    async def start(self, video_id: str) -> None:
        """
        コメント監視を開始する
        
        Args:
            video_id: 動画ID
        """
        self._running = True
        self._current_video_id = video_id
        
        try:
            # pytchatでコメント取得を開始
            self._chat = pytchat.create(video_id)
            
            # コメント監視タスクを開始
            asyncio.create_task(self._listen_comments())
            logger.info(f"コメント監視を開始しました: {video_id}")
            
        except Exception as e:
            logger.error(f"コメント監視開始エラー: {e}")
            self._running = False
    
    async def stop(self) -> None:
        """コメント監視を停止する"""
        self._running = False
        logger.info("コメント監視を停止しました")
    
    async def get_next_comment(self) -> Optional[Comment]:
        """
        次のコメントを取得する
        
        Returns:
            Optional[Comment]: コメントデータ（コメントがない場合はNone）
        """
        try:
            return await asyncio.wait_for(self._comment_queue.get(), timeout=0.1)
        except asyncio.TimeoutError:
            return None
    
    async def _listen_comments(self) -> None:
        """コメントを監視する"""
        while self._running:
            try:
                if not self._chat or not self._chat.is_alive():
                    logger.error("チャットが開始されていません")
                    await asyncio.sleep(5)
                    continue
                
                # コメントを取得
                comments = json.loads(self._chat.get().json())
                if not comments:
                    await asyncio.sleep(1)
                    continue
                
                # 最新のコメントを処理
                latest_comment = comments[-1]
                message = latest_comment.get("message")
                author = latest_comment.get("author")
                
                # 作者名を取得
                if isinstance(author, dict) and "name" in author:
                    author_name = author["name"]
                else:
                    author_name = str(author)
                
                # コメントを作成
                comment = Comment(
                    id=latest_comment.get("id", ""),
                    author=author_name,
                    text=message,
                    timestamp=datetime.now(timezone.utc)  # pytchatでは時刻情報が取得できないため現在時刻を使用
                )
                
                await self._comment_queue.put(comment)
                logger.info(f"新しいコメントを受信: {comment.author}: {comment.text}")
                
                # ポーリング間隔
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"コメント監視エラー: {e}")
                await asyncio.sleep(5) 