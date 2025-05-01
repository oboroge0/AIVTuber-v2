"""
コントローラーモジュール
"""
import asyncio
import json
import os
from typing import List, Optional
from datetime import datetime

from .comment_listener import CommentListener
from .scorer import CommentScorer
from .memory_search import MemorySearcher
from .prompt_builder import PromptBuilder
from .responder import Responder
from .tts_handler import TTSHandler
from .vts_animator import VTSAnimator
from .obs_connector import OBSConnector
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
        self.prompt_builder = PromptBuilder()
        self.responder = Responder()
        self.tts_handler = TTSHandler()
        self.vts_animator = VTSAnimator()
        self.obs_connector = OBSConnector()
        
        self.history: List[str] = []
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
            
            # 履歴を読み込む
            self.load_history()
            
            # コメントリスナーを開始
            await self.comment_listener.start(video_id)
            
            logger.info(f"コメントリスナーを開始しました: {video_id}")
            
            # メインループを開始
            # 現在のイベントループを取得
            loop = asyncio.get_running_loop()
            # メインループタスクを作成して実行
            self._main_loop_task = loop.create_task(self._main_loop())
            logger.info("メインループを開始しました")
            
        except Exception as e:
            logger.error(f"配信開始エラー: {e}")
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """配信を停止する"""
        self.is_running = False
        
        # メインループタスクをキャンセル
        if self._main_loop_task:
            self._main_loop_task.cancel()
            try:
                await self._main_loop_task
            except asyncio.CancelledError:
                pass
            self._main_loop_task = None
        
        # コメントリスナーを停止
        await self.comment_listener.stop()
        
        # 履歴を保存
        await self.save_history()
        
        logger.info("配信を停止しました")
    
    async def speak_text(self, text: str) -> None:
        """
        テキストを音声で再生する
        
        Args:
            text: 再生するテキスト
        """
        try:
            # 音声合成と再生
            self.tts_handler.text_to_speech(text)
            
            # アニメーション
            await self.vts_animator.trigger_random_animation("Speak")
            
        except Exception as e:
            logger.error(f"Error speaking text: {e}")
    
    def load_history(self) -> None:
        """履歴を読み込む"""
        try:
            data = load_json_file(Config.CURRENT_HISTORY_FILE)
            self.history = data.get("history", [])
        except Exception as e:
            logger.error(f"Error loading history: {e}")
            self.history = []
    
    async def save_history(self) -> None:
        """履歴を保存する"""
        try:
            data = {"history": self.history}
            save_json_file(Config.CURRENT_HISTORY_FILE, data)
            await create_backup(Config.CURRENT_HISTORY_FILE, Config.BACKUPS_DIR)
        except Exception as e:
            logger.error(f"Error saving history: {e}")
    
    async def _main_loop(self) -> None:
        """メインループ"""
        try:
            logger.info("メインループを開始します")
            while self.is_running:
                try:
                    # コメントを取得
                    comment = await self.comment_listener.get_next_comment()
                    if comment is not None:
                        logger.info(f"コメント: {comment.text}") #debug
                        # スコアリング
                        score = self.scorer.score_comment(comment)
                        logger.info(f"スコア: {score}") #debug
                        if score > 0.3:  # スコアが0.3以上のコメントのみ処理
                            # 応答を生成
                            response = await self._full_response_pipeline(comment.text)
                            # 音声合成と再生
                            await self.speak_text(response)
                    
                    # イベントループに制御を戻す
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
        memories = await self.memory_searcher.search_memory(user_text)
        
        # プロンプトを構築
        prompt = self.prompt_builder.build_prompt(
            comment=user_text,
            memory=memories,
            history=self.history
        )
        
        # 応答を生成
        response = await self.responder.generate_response(prompt)

        # 履歴を更新
        self._update_history(user_text, response)
        
        return response
    
    def _current_keywords(self) -> List[str]:
        """
        現在のキーワードを取得
        
        Returns:
            キーワードのリスト
        """
        # 履歴からキーワードを抽出
        keywords = []
        for item in self.history[-5:]:  # 最新の5件から抽出
            keywords.extend(item.split())
        
        # 重複を除去
        keywords = list(set(keywords))
        
        return keywords
    
    def _update_history(self, user: str, ai: str) -> None:
        """
        履歴を更新
        
        Args:
            user: ユーザーのテキスト
            ai: AIの応答
        """
        # 履歴に追加
        self.history.append(f"User: {user}")
        self.history.append(f"AI: {ai}")
        
        # 履歴が長すぎる場合は古いものを削除
        if len(self.history) > 100:
            self.history = self.history[-100:] 