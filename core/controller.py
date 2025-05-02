"""
コントローラーモジュール
"""
import asyncio
import json
import os
from typing import List, Optional
from datetime import datetime
from pathlib import Path

from .comment_listener import CommentListener
from .scorer import CommentScorer
from .memory_search import MemorySearcher
from .prompt_builder import PromptBuilder
from .responder import Responder
from .tts_handler import TTSHandler
from .vts_animator import VTSAnimator
from .obs_connector import OBSConnector
from .history_manager import HistoryManager
from .models import Comment
from utils.logger import get_logger
from utils.helpers import load_json_file, save_json_file, create_backup
from core.config import Config

logger = get_logger(__name__)

class AIVTuberController:
    """AIVTuberコントローラー"""
    
    def __init__(self):
        """初期化"""
        # Producer–Consumer 共有キュー
        self._comment_queue: asyncio.Queue = asyncio.Queue()
        
        self.scorer = CommentScorer()
        self.memory_searcher = MemorySearcher()
        self.history = HistoryManager(
            max_turns=Config.MAX_HISTORY_TURNS,
            persist_dir=Path(Config.HISTORY_DIR),
            backup_dir=Path(Config.BACKUPS_DIR)
        )
        self.prompt_builder = PromptBuilder(
            self.history,
            system_prompt_path=Config.DEFAULT_PROMPT_FILE
        )
        self.responder = Responder()
        self.tts_handler = TTSHandler()
        self.vts_animator = VTSAnimator()
        self.obs_connector = OBSConnector()
        
        self.current_video_id: Optional[str] = None
        self.is_running = False
        self._listener = None
    
    async def start(self, video_id: str) -> None:
        """
        配信を開始する
        
        Args:
            video_id: YouTubeの動画ID
        """
        try:
            self.current_video_id = video_id
            self.is_running = True
            
            # --- Producer タスク：CommentListener ---
            self._listener = CommentListener(video_id, self._comment_queue)
            asyncio.create_task(self._listener.start())   # Producer 起動
            
            # --- Consumer タスク：コメント処理メインループ ---
            asyncio.create_task(self._consume_comments())  # Consumer 起動
            
            logger.info(f"配信を開始しました: {video_id}")
            
        except Exception as e:
            logger.error(f"配信開始エラー: {e}")
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """配信を停止する"""
        self.is_running = False
        
        if self._listener:
            await self._listener.stop()
        
        logger.info("配信を停止しました")
    
    async def _speak(self, text: str) -> None:
        """
        テキストを音声で再生する
        
        Args:
            text: 再生するテキスト
        """
        try:
            # --- TTS 音声合成（Executor で非同期実行） ---
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,  # default ThreadPoolExecutor
                self.tts_handler.text_to_speech,
                text,
            )
            await self.vts_animator.trigger_random_animation("Speak")
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
    
    async def _consume_comments(self):
        """Queue からコメントを取り出して順次処理する Consumer ループ"""
        while self.is_running:
            try:
                comment = await self._comment_queue.get()
                await self._handle_comment(comment)
            except Exception as e:
                logger.exception(e)
            finally:
                self._comment_queue.task_done()
    
    async def _handle_comment(self, comment: Comment):
        """個別コメントを処理するロジック（スコアリング → GPT 応答 → TTS）"""
        score = self.scorer.score_comment(comment)
        if score < Config.THRESHOLD:
            return
            
        response_text = await self._full_response_pipeline(comment.text)
        await self._speak(response_text)
    
    async def _full_response_pipeline(self, user_text: str) -> str:
        """
        完全な応答パイプライン
        
        Args:
            user_text: ユーザーのテキスト
            
        Returns:
            生成された応答
        """
        # 関連する記憶を検索
        memory_snippet = self.memory_searcher.search_memory(user_text)
        
        # プロンプトを構築
        prompt = self.prompt_builder.build(comment=user_text, rag_memory=memory_snippet)
        
        # 応答を生成
        response = await self.responder.generate_response(prompt)

        # 履歴を更新
        self.history.append("user", user_text)
        self.history.append("assistant", response)
        
        return response 