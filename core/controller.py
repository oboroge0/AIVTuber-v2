"""
コントローラーモジュール
"""
import asyncio
from typing import Optional
from pathlib import Path
from datetime import datetime

from .comment_listener import CommentListener
from .voice_listener import VoiceListener
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
import time

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
        self._voice_listener: Optional[VoiceListener] = None
        self._is_comment_processing = True  # コメント処理状態フラグ
        
        # 音声認識関連
        self.operation_mode = Config.OPERATION_MODE  # "chat", "voice", "hybrid"
        self.voice_detected = False
        self.last_voice_time = time.time()
        self.voice_priority_mode = False
    
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
            self.vts_animator.start()
            
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
    
    async def start_voice_mode(self) -> None:
        """
        音声のみモードで開始する（配信なし）
        """
        try:
            self.operation_mode = "voice"
            self.is_running = True
            
            # VTSアニメーターを起動（ローカルでも動作）
            self.vts_animator.start()
            
            # 音声リスナーを初期化
            self._voice_listener = VoiceListener(self._comment_queue)
            await self._voice_listener.start()
            
            # コメント処理ループを開始
            asyncio.create_task(self._consume_comments())
            
            # 発話処理を開始
            await self.speak.start()
            
            logger.info("音声モードを開始しました")
            
        except Exception as e:
            logger.error(f"音声モード開始エラー: {e}")
            self.is_running = False
            raise
    
    async def start_hybrid_mode(self, video_id: str) -> None:
        """
        ハイブリッドモードで開始する（配信＋音声）
        
        Args:
            video_id: YouTubeの動画ID
        """
        try:
            self.operation_mode = "hybrid"
            self.voice_priority_mode = True
            
            # 通常の配信開始処理
            await self.start(video_id)
            
            # 音声リスナーも追加で開始
            self._voice_listener = VoiceListener(self._comment_queue)
            await self._voice_listener.start()
            
            logger.info("ハイブリッドモードを開始しました")
            
        except Exception as e:
            logger.error(f"ハイブリッドモード開始エラー: {e}")
            self.is_running = False
            raise
    
    async def stop(self) -> None:
        """配信を停止する"""
        self.is_running = False
        
        if self._listener:
            await self._listener.stop()
            
        if self._voice_listener:
            await self._voice_listener.stop()
        
        # 発話処理を停止
        await self.speak.stop()
        
        logger.info(f"{self.operation_mode}モードを停止しました")
    
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

                # 発話キューが満杯の場合はスキップ
                if self.speak._queue.full():
                    logger.warning("発話キューが満杯のため、コメントをスキップしました")
                    if not self._comment_queue.empty():
                        self._comment_queue.task_done()
                    await asyncio.sleep(0.1)
                    continue

                # コメントがある場合は優先的に処理
                if not self._comment_queue.empty():
                    comment = await self._comment_queue.get()
                    
                    # ハイブリッドモードで音声入力の場合は最優先処理
                    if self.operation_mode == "hybrid" and comment.source == "voice":
                        self.voice_detected = True
                        self.last_voice_time = time.time()
                        # 他のコメントをスキップする場合はここで処理
                        
                    await self._handle_comment(comment)
                    logger.info(f"コメントを処理しました ({comment.source})") #debug
                    self._comment_queue.task_done()
                    continue

                # コメントがなく、発話中でない場合のみ継続応答を生成
                if not self.speak.is_speaking() and not self.speak._queue.full():
                    # ハイブリッドモードの場合、音声入力から一定時間経過していることを確認
                    if self.operation_mode == "hybrid":
                        time_since_voice = time.time() - self.last_voice_time
                        if time_since_voice < 10:  # 音声入力から10秒以内は継続応答を控える
                            await asyncio.sleep(1)
                            continue
                    
                    await self._generate_continuation_response()
                    logger.info("継続応答を生成しました") #debug
                
                await asyncio.sleep(2)

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
        self.memory.add(f"{comment.author}: {comment.text}", {
            "role": "user",
            "timestamp": datetime.now().isoformat()
        })
        self.memory.add(response_text, {
            "role": "assistant",
            "timestamp": datetime.now().isoformat()
        })
        
        # 履歴を更新
        self.history.append("user", f"{comment.author}: {comment.text}")
        self.history.append("assistant", response_text)
        
        await self.speak.add_speech(response_text)

    async def _generate_continuation_response(self):
        """コメントがない場合の継続応答を生成"""
        try:
            prompt = self.prompt_builder.build(
                comment="<system>直前の会話の内容を読み取り、自然に会話を展開してください。</system>",
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
    
    def set_operation_mode(self, mode: str) -> None:
        """
        動作モードを設定する
        
        Args:
            mode: "chat", "voice", "hybrid"のいずれか
        """
        if mode not in ["chat", "voice", "hybrid"]:
            raise ValueError(f"無効なモード: {mode}")
        
        self.operation_mode = mode
        self.voice_priority_mode = (mode == "hybrid")
        logger.info(f"動作モードを{mode}に設定しました")
    
    def get_voice_status(self) -> dict:
        """音声認識の状態を取得する"""
        if self._voice_listener:
            return self._voice_listener.get_status()
        else:
            return {
                "is_listening": False,
                "audio_level": 0,
                "interim_text": "",
                "error_count": 0,
                "mic_device": None
            }