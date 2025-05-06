"""
発話管理モジュール
"""
import os
import json
import torch
import numpy as np
import sounddevice as sd
import asyncio
from typing import Optional
from pathlib import Path
from style_bert_vits2.nlp import bert_models
from style_bert_vits2.tts_model import TTSModel
from style_bert_vits2.constants import Languages
from utils.logger import get_logger
from .obs_connector import OBSConnector
from core.config import Config
import wave
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor

logger = get_logger(__name__)

class Speak:
    """発話キューを管理するクラス"""
    
    def __init__(self):
        """初期化"""
        self._queue: asyncio.Queue[np.ndarray] = asyncio.Queue(maxsize=50)  # 最大50件のキュー
        self._is_processing = True
        self._current_task: Optional[asyncio.Task] = None
        self._obs_connector = OBSConnector()
        self._last_activity = None
        self._is_speaking = False  # 発話状態のフラグ
        
        # TTS関連の初期化
        self.device = Config.VOICE_MODEL["model"]["device"]
        self._load_models()
        
    def _load_models(self):
        """モデルの読み込み"""
        try:
            # BERTモデルの読み込み
            bert_models.load_model(Languages.JP, Config.VOICE_MODEL["bert"]["model"])
            bert_models.load_tokenizer(Languages.JP, Config.VOICE_MODEL["bert"]["tokenizer"])
            
            # TTSモデルの読み込み
            model_path = os.path.join(Config.VOICE_MODEL_DIR, Config.VOICE_MODEL["model"]["file"])
            config_path = os.path.join(Config.VOICE_MODEL_DIR, Config.VOICE_MODEL["model"]["config"])
            style_vectors_path = os.path.join(Config.VOICE_MODEL_DIR, Config.VOICE_MODEL["model"]["style_vectors"])
            
            with open(config_path, "r", encoding="utf-8") as f:
                self.config = json.load(f)
            
            self.tts_model = TTSModel(
                model_path=model_path, 
                config_path=config_path,
                style_vec_path=style_vectors_path,
                device=self.device
            )
            
            logger.info("TTS models loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load TTS models: {e}")
            raise
        
    async def start(self):
        """発話処理を開始する"""
        self._is_processing = True
        self._last_activity = None
        self._current_task = asyncio.create_task(self._process_queue())
        logger.info("発話処理を開始しました")
    
    async def stop(self):
        """発話処理を停止する"""
        self._is_processing = False
        if self._current_task:
            self._current_task.cancel()
            try:
                await self._current_task
            except asyncio.CancelledError:
                pass
        logger.info("発話処理を停止しました")
    
    async def add_speech(self, text: str):
        """発話キューにテキストを追加する"""
        try:
            # テキストを改行で分割
            sentences = [s.strip() for s in text.split('\n') if s.strip()]
            
            for sentence in sentences:
                # キューが満杯の場合はスキップ
                if self._queue.full():
                    logger.warning("発話キューが満杯のため、発話をスキップしました")
                    return
                
                # OBSの字幕を更新
                self._obs_connector.set_answer(sentence)
                
                # テキストを音声に変換
                audio = await self._text_to_speech(sentence)
                
                # キューに追加
                await self._queue.put(audio)
                self._last_activity = asyncio.get_event_loop().time()
                
        except Exception as e:
            logger.error(f"発話追加エラー: {e}")
    
    async def _process_queue(self):
        """キューから発話を順次処理する"""
        try:
            while self._is_processing:
                try:
                    # キューから音声データを取得
                    audio = await self._queue.get()
                    
                    # 発話開始
                    self._is_speaking = True
                    
                    # 音声を再生
                    sd.play(audio)
                    sd.wait()
                    
                    # 発話終了
                    self._is_speaking = False
                    
                    # タスク完了を通知
                    self._queue.task_done()
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error(f"音声再生エラー: {e}")
                    self._is_speaking = False
                    continue
                    
        finally:
            sd.stop()
            self._is_speaking = False
    
    async def _text_to_speech(self, text: str) -> np.ndarray:
        """テキストを音声に変換して再生"""
        try:
            # 音声合成
            sr, audio = self.tts_model.infer(text=text, length=0.8)
            
            # 音声データを正規化
            audio = audio / np.max(np.abs(audio))
            return audio
            
        except Exception as e:
            logger.error(f"Failed to synthesize and play speech: {e}")
            raise
    
    def toggle_processing(self):
        """発話処理の状態を切り替える"""
        self._is_processing = not self._is_processing
        status = "再開" if self._is_processing else "一時停止"
        logger.info(f"発話処理を{status}しました")
    
    def is_processing(self) -> bool:
        """発話処理の状態を取得する"""
        return self._is_processing
    
    def is_speaking(self) -> bool:
        """発話状態を取得する"""
        return self._is_speaking 