"""
コントローラーモジュール
"""
import asyncio
from typing import Optional
from pathlib import Path

from .comment_listener import CommentListener
from .scorer import CommentScorer
from .memory_search import MemorySearcher
from .prompt_builder import PromptBuilder
from .responder import Responder
from .vts_animator import VTSAnimator
from .obs_connector import OBSConnector
from .history_manager import HistoryManager
from .models import Comment
from utils.logger import get_logger
from core.config import Config
from memory.hipporag_memory import VTuberMemory
import torch
from .speech import Speak

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
        
        # --- HippoRAG 長期記憶を初期化 ---
        self.memory = VTuberMemory(model_name="cl-nagoya/sup-simcse-ja-large", use_gpu=torch.cuda.is_available())
        
        self.prompt_builder = PromptBuilder(
            self.history,
            memory=self.memory
        )
        self.responder = Responder(Config.DEFAULT_PROMPT_FILE)
        self.speak = Speak()
        self.vts_animator = VTSAnimator()
        self.obs_connector = OBSConnector()
        
        self.current_video_id: Optional[str] = None
        self.current_theme: Optional[str] = None
        self.is_running = False
        self._listener = None
        self._is_comment_processing = True  # コメント処理状態フラグ
    
    def set_theme(self, theme: str) -> None:
        """
        現在の配信テーマを設定する
        
        Args:
            theme: 設定するテーマ
        """
        self.current_theme = theme
        logger.info(f"配信テーマを設定しました: {theme}")
    
    async def start(self, video_id: str) -> None:
        """
        配信を開始する
        
        Args:
            video_id: YouTubeの動画ID
        """
        try:
            self.current_video_id = video_id
            self.is_running = True
            
            # OBSのチャットURLを設定
            self.obs_connector.set_chat_url(video_id)

            # ランダムなアニメーションをトリガー
            #self.vts_animator.start()
            
            # --- Producer タスク：CommentListener ---
            self._listener = CommentListener(video_id, self._comment_queue)
            asyncio.create_task(self._listener.start())   # Producer 起動
            
            # --- Consumer タスク：コメント処理メインループ ---
            asyncio.create_task(self._consume_comments())  # Consumer 起動
            
            # 発話処理を開始
            await self.speak.start()
            
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
        
        # 発話処理を停止
        await self.speak.stop()
        
        logger.info("配信を停止しました")
    
    async def _speak(self, text: str) -> None:
        """
        テキストを音声で再生する
        
        Args:
            text: 再生するテキスト
        """
        await self.speak.add_speech(text)
    
    async def _consume_comments(self):
        """Queue からコメントを取り出して順次処理する Consumer ループ"""
        while self.is_running:
            try:
                # コメント処理が一時停止中の場合は待機
                if not self._is_comment_processing:
                    await asyncio.sleep(1)
                    continue

                # キューが空の場合、会話を継続
                if self._comment_queue.empty():
                    await self._generate_continuation_response()
                    continue

                # コメントがある場合は通常通り処理
                comment = await self._comment_queue.get()
                await self._handle_comment(comment)
                self._comment_queue.task_done()  # タスク完了を通知
            except Exception as e:
                logger.exception(e)
                if not self._comment_queue.empty():
                    self._comment_queue.task_done()
    
    async def _handle_comment(self, comment: Comment):
        """個別コメントを処理するロジック（スコアリング → GPT 応答 → TTS）"""
        score = self.scorer.score_comment(comment)
        if score < Config.THRESHOLD:
            return
            
        # プロンプトを構築（テーマを含める）
        prompt = self.prompt_builder.build(
            comment=f"{comment.author}: {comment.text}",
            current_theme=self.current_theme
        )
        
        # 応答を生成
        response_text = await self.responder.generate_response(prompt)

        # 長期記憶に追加
        self.memory.add(f"{comment.author}: {comment.text}", {"role": "user"})
        self.memory.add(response_text, {"role": "assistant"})
        
        # 履歴を更新
        self.history.append("user", f"{comment.author}: {comment.text}")
        self.history.append("assistant", response_text)
        
        await self.speak.add_speech(response_text)

    async def _generate_continuation_response(self):
        """コメントがない場合の継続応答を生成"""
        try:
            prompt = self.prompt_builder.build(
                comment="自然に会話を継続してください。",
                current_theme=self.current_theme
            )
            
            # 応答を生成
            response_text = await self.responder.generate_response(prompt)
            
            # 履歴を更新
            self.memory.add(response_text, {"role": "assistant"})
            self.history.append("assistant", response_text)
            
            # 発話
            await self.speak.add_speech(response_text)
            
        except Exception as e:
            logger.error(f"継続応答生成エラー: {e}")

    def pause_comment_processing(self) -> None:
        """コメント処理を一時停止する"""
        self._is_comment_processing = False
        logger.info("コメント処理を一時停止しました")

    def resume_comment_processing(self) -> None:
        """コメント処理を再開する"""
        self._is_comment_processing = True
        logger.info("コメント処理を再開しました")

    def is_comment_processing(self) -> bool:
        """コメント処理状態を取得する"""
        return self._is_comment_processing