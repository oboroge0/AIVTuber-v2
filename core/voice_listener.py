"""
音声認識リスナーモジュール
Google Speech-to-Textを使用した音声入力の処理
"""
import asyncio
import io
import os
import queue
import threading
from typing import Optional
from datetime import datetime, timezone

import pyaudio
import speech_recognition as sr
from google.cloud import speech
from google.api_core import exceptions

from .models import Comment
from utils.logger import get_logger

logger = get_logger(__name__)

class VoiceListener:
    """Google STTを使用した音声認識リスナー"""
    
    def __init__(self, comment_queue: asyncio.Queue):
        """
        初期化
        
        Args:
            comment_queue: コメントキュー（既存のものと共有）
        """
        self._running = False
        self._comment_queue = comment_queue
        self._audio_queue: queue.Queue = queue.Queue()
        
        # Google STT設定
        self.client = None
        self.config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="ja-JP",
            enable_automatic_punctuation=True,
            model="latest_long"
        )
        self.streaming_config = speech.StreamingRecognitionConfig(
            config=self.config,
            interim_results=True,
            single_utterance=False
        )
        
        # PyAudio設定
        self.pyaudio = None
        self.stream = None
        self.sample_rate = 16000
        self.chunk_size = 1024
        
        # 音声認識の状態
        self.is_listening = False
        self.current_interim_text = ""
        self.audio_level = 0
        self.mic_device_index = None
        
        # エラーカウンター
        self.error_count = 0
        self.max_errors = 5
        
    def initialize_google_stt(self):
        """Google STTクライアントを初期化"""
        try:
            self.client = speech.SpeechClient()
            logger.info("Google STTクライアントを初期化しました")
        except Exception as e:
            logger.error(f"Google STT初期化エラー: {e}")
            raise
            
    def list_microphones(self):
        """利用可能なマイクデバイスのリストを取得"""
        if not self.pyaudio:
            self.pyaudio = pyaudio.PyAudio()
            
        devices = []
        for i in range(self.pyaudio.get_device_count()):
            info = self.pyaudio.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels']
                })
        return devices
    
    async def start(self, mic_index: Optional[int] = None) -> None:
        """
        音声認識を開始する
        
        Args:
            mic_index: 使用するマイクのインデックス（Noneの場合はデフォルト）
        """
        self._running = True
        self.mic_device_index = mic_index
        
        try:
            # Google STTクライアントを初期化
            if not self.client:
                self.initialize_google_stt()
            
            # PyAudioを初期化
            if not self.pyaudio:
                self.pyaudio = pyaudio.PyAudio()
            
            # 音声ストリームを開始
            self._start_audio_stream()
            
            # 音声認識タスクを開始
            asyncio.create_task(self._recognize_stream())
            
            logger.info("音声認識を開始しました")
            
        except Exception as e:
            logger.error(f"音声認識開始エラー: {e}")
            self._running = False
            raise
    
    async def stop(self) -> None:
        """音声認識を停止する"""
        self._running = False
        self.is_listening = False
        
        # 音声ストリームを停止
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
            
        # PyAudioを終了
        if self.pyaudio:
            self.pyaudio.terminate()
            self.pyaudio = None
            
        logger.info("音声認識を停止しました")
    
    def _start_audio_stream(self):
        """音声入力ストリームを開始"""
        try:
            stream_params = {
                'format': pyaudio.paInt16,
                'channels': 1,
                'rate': self.sample_rate,
                'input': True,
                'frames_per_buffer': self.chunk_size,
                'stream_callback': self._audio_callback
            }
            
            if self.mic_device_index is not None:
                stream_params['input_device_index'] = self.mic_device_index
                
            self.stream = self.pyaudio.open(**stream_params)
            self.stream.start_stream()
            self.is_listening = True
            
        except Exception as e:
            logger.error(f"音声ストリーム開始エラー: {e}")
            raise
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """音声データのコールバック"""
        if self._running:
            # 音声レベルを計算（簡易版）
            audio_data = list(in_data)
            self.audio_level = max(audio_data) if audio_data else 0
            
            # キューに追加
            self._audio_queue.put(in_data)
            
        return (in_data, pyaudio.paContinue)
    
    async def _recognize_stream(self):
        """ストリーミング音声認識を実行"""
        while self._running:
            try:
                # 音声データジェネレータを作成
                audio_generator = self._audio_generator()
                
                # リクエストを作成
                requests = (speech.StreamingRecognizeRequest(audio_content=chunk)
                          for chunk in audio_generator)
                
                # ストリーミング認識を実行
                responses = self.client.streaming_recognize(
                    self.streaming_config, 
                    requests
                )
                
                # 認識結果を処理
                await self._process_responses(responses)
                
            except exceptions.OutOfRange:
                # ストリーミングの時間制限に達した場合は再開
                logger.info("ストリーミング時間制限に達しました。再開します。")
                continue
                
            except Exception as e:
                logger.error(f"音声認識エラー: {e}")
                self.error_count += 1
                
                if self.error_count >= self.max_errors:
                    logger.error("エラー回数が上限に達しました。音声認識を停止します。")
                    await self.stop()
                    break
                    
                await asyncio.sleep(1)
    
    def _audio_generator(self):
        """音声データのジェネレータ"""
        while self._running:
            try:
                # タイムアウト付きでキューから取得
                chunk = self._audio_queue.get(timeout=0.1)
                yield chunk
            except queue.Empty:
                continue
    
    async def _process_responses(self, responses):
        """認識結果を処理"""
        for response in responses:
            if not response.results:
                continue
                
            for result in response.results:
                if not result.alternatives:
                    continue
                    
                transcript = result.alternatives[0].transcript
                
                if result.is_final:
                    # 確定したテキストをコメントとして処理
                    await self._create_voice_comment(transcript)
                    self.current_interim_text = ""
                else:
                    # 途中経過を保存（UIに表示用）
                    self.current_interim_text = transcript
    
    async def _create_voice_comment(self, text: str):
        """音声入力をCommentオブジェクトとして作成"""
        if not text.strip():
            return
            
        comment = Comment(
            id=f"voice_{datetime.now().timestamp()}",
            author="配信者",
            text=text,
            timestamp=datetime.now(timezone.utc),
            source="voice",  # 音声入力を識別
            priority="high",  # 音声は高優先度
            is_voice_input=True
        )
        
        # キューに追加
        await self._comment_queue.put(comment)
        logger.info(f"音声認識: {text}")
        
        # エラーカウントをリセット（成功したので）
        self.error_count = 0
    
    def get_status(self) -> dict:
        """音声認識の状態を取得"""
        return {
            "is_listening": self.is_listening,
            "audio_level": self.audio_level,
            "interim_text": self.current_interim_text,
            "error_count": self.error_count,
            "mic_device": self.mic_device_index
        }
    
    def set_mic_sensitivity(self, threshold: int):
        """マイクの感度を設定"""
        # この実装では使用しないが、将来の拡張用
        pass