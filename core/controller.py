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
from utils.logger import get_logger
from utils.helpers import load_json_file, save_json_file, create_backup
from core.config import Config

logger = get_logger(__name__)

class AIVTuberController:
    """AIVTuberコントローラー"""
    
    def __init__(self):
        """初期化"""
        self.comment_listener = CommentListener()
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
        self._main_loop_task = None
    
    async def start(self, video_id: str) -> None:
        """
        配信を開始する
        
        Args:
            video_id: YouTubeの動画ID
        """
        try:
            self.current_video_id = video_id
            self.is_running = True
            
            # コメントリスナーを開始
            await self.comment_listener.start(video_id)
            
            logger.info(f"コメントリスナーを開始しました: {video_id}")
            
            # メインループを開始
            loop = asyncio.get_running_loop()
            self._main_loop_task = loop.create_task(self._main_loop())
            logger.info("メインループを開始しました")
            
        except Exception as e:
            logger.error(f"配信開始エラー: {e}")
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """配信を停止する"""
        self.is_running = False
        
        if self._main_loop_task:
            self._main_loop_task.cancel()
            try:
                await self._main_loop_task
            except asyncio.CancelledError:
                pass
            self._main_loop_task = None
        
        await self.comment_listener.stop()
        logger.info("配信を停止しました")
    
    async def speak_text(self, text: str) -> None:
        """
        テキストを音声で再生する
        
        Args:
            text: 再生するテキスト
        """
        try:
            self.tts_handler.text_to_speech(text)
            await self.vts_animator.trigger_random_animation("Speak")
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
    
    async def _main_loop(self) -> None:
        """メインループ"""
        try:
            logger.info("メインループを開始します")
            while self.is_running:
                try:
                    comment = await self.comment_listener.get_next_comment()
                    if comment is not None:
                        logger.info(f"コメント: {comment.text}")
                        score = self.scorer.score_comment(comment)
                        logger.info(f"スコア: {score}")
                        if score > 0.3:
                            response = await self._full_response_pipeline(comment.text)
                            await self.speak_text(response)
                    
                    await asyncio.sleep(0)
                    
                except Exception as e:
                    logger.error(f"メインループ内でエラーが発生: {e}")
                    await asyncio.sleep(1)
        except asyncio.CancelledError:
            logger.info("メインループがキャンセルされました")
        except Exception as e:
            logger.error(f"メインループで予期せぬエラーが発生: {e}")
            self.is_running = False
    
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