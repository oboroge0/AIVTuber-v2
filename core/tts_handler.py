"""
Text-to-Speech処理モジュール
"""
import os
import json
import torch
import numpy as np
import sounddevice as sd
from pathlib import Path
from style_bert_vits2.nlp import bert_models
from style_bert_vits2.tts_model import TTSModel
from style_bert_vits2.constants import Languages
from core.config import Config
from utils.logger import get_logger

logger = get_logger(__name__)

class TTSHandler:
    """TTS処理クラス"""
    
    def __init__(self):
        """初期化"""
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
    
    def text_to_speech(self, text, speed=0.95):
        """テキストを音声に変換して再生"""
        try:
            # 音声合成
            sr, audio = self.tts_model.infer(text=text, length=speed)
            
            # 音声再生
            sd.play(audio, sr)
            sd.wait()
            
        except Exception as e:
            logger.error(f"Failed to synthesize and play speech: {e}")