"""
コントロールAPIモジュール
"""
import json
import asyncio
from fastapi import FastAPI, WebSocket
from pydantic import BaseModel
from typing import Optional
from core.controller import AIVTuberController
from utils.logger import get_logger
from core.config import Config
import queue

logger = get_logger(__name__)

# FastAPIアプリケーション
app = FastAPI(title="AIVTuber Control API")

# コントローラー
controller = AIVTuberController()

# WebSocket接続
websocket: Optional[WebSocket] = None

# アプリケーション起動時のイベント
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info("APIサーバーを起動しました")

# アプリケーション終了時のイベント
@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("APIサーバーを停止します")
    if controller.is_running:
        await controller.stop()

class StartRequest(BaseModel):
    """配信開始リクエスト"""
    video_id: str

class SpeakRequest(BaseModel):
    """発話リクエスト"""
    text: str

class SetThemeRequest(BaseModel):
    """テーマ設定リクエスト"""
    theme: str

class SetModeRequest(BaseModel):
    """動作モード設定リクエスト"""
    mode: str  # "chat", "voice", "hybrid"

class VoiceStartRequest(BaseModel):
    """音声認識開始リクエスト"""
    mic_index: Optional[int] = None

@app.post("/start")
async def start_stream(request: StartRequest):
    """配信を開始する"""
    try:
        # モードに応じて適切な開始メソッドを呼び出す
        if controller.operation_mode == "chat":
            await controller.start(request.video_id)
        elif controller.operation_mode == "voice":
            await controller.start_voice_mode()
        elif controller.operation_mode == "hybrid":
            await controller.start_hybrid_mode(request.video_id)
        else:
            return {"status": "error", "message": f"無効なモード: {controller.operation_mode}"}
            
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error starting stream: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/stop")
async def stop_stream():
    """配信を停止する"""
    try:
        await controller.stop()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error stopping stream: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/speak")
async def speak_text(request: SpeakRequest):
    """テキストを読み上げる"""
    try:
        await controller.speak_text(request.text)
        print("speak_text") #debug
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error speaking text: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/set_theme")
async def set_theme(request: SetThemeRequest):
    """配信テーマを設定する"""
    try:
        controller.set_theme(request.theme)
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error setting theme: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/status")
async def get_status():
    """ステータスを取得する"""
    return {
        "is_running": controller.is_running,
        "current_video_id": controller.current_video_id,
        "is_comment_processing": controller.is_comment_processing(),
        "operation_mode": controller.operation_mode,
        "voice_status": controller.get_voice_status()
    }

@app.post("/mode/set")
async def set_mode(request: SetModeRequest):
    """動作モードを設定する"""
    try:
        controller.set_operation_mode(request.mode)
        return {"status": "success", "mode": request.mode}
    except Exception as e:
        logger.error(f"Error setting mode: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/voice/start")
async def start_voice_recognition(request: VoiceStartRequest):
    """音声認識を開始する（音声モード用）"""
    try:
        if controller.operation_mode == "voice":
            await controller.start_voice_mode()
        elif controller.operation_mode == "hybrid" and controller.current_video_id:
            await controller.start_hybrid_mode(controller.current_video_id)
        else:
            return {"status": "error", "message": "音声認識の開始には適切なモード設定が必要です"}
        
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error starting voice recognition: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/voice/stop")
async def stop_voice_recognition():
    """音声認識を停止する"""
    try:
        if controller._voice_listener:
            await controller._voice_listener.stop()
            controller._voice_listener = None
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error stopping voice recognition: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/voice/status")
async def get_voice_status():
    """音声認識の状態を取得する"""
    return controller.get_voice_status()

@app.get("/voice/devices")
async def get_audio_devices():
    """利用可能なオーディオデバイスのリストを取得する"""
    try:
        from core.voice_listener import VoiceListener
        temp_listener = VoiceListener(None)
        devices = temp_listener.list_microphones()
        return {"status": "success", "devices": devices}
    except Exception as e:
        logger.error(f"Error getting audio devices: {e}")
        return {"status": "error", "message": str(e), "devices": []}

@app.post("/pause_comment_processing")
async def pause_comment_processing():
    """コメント処理を一時停止する"""
    try:
        controller.pause_comment_processing()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error pausing comment processing: {e}")
        return {"status": "error", "message": str(e)}

@app.post("/resume_comment_processing")
async def resume_comment_processing():
    """コメント処理を再開する"""
    try:
        controller.resume_comment_processing()
        return {"status": "success"}
    except Exception as e:
        logger.error(f"Error resuming comment processing: {e}")
        return {"status": "error", "message": str(e)}

@app.websocket("/logs")
async def websocket_endpoint(ws: WebSocket):
    """WebSocketエンドポイント"""
    global websocket
    await ws.accept()
    websocket = ws
    
    try:
        while True:
            try:
                # ログキューからメッセージを取得
                log_record = await asyncio.get_event_loop().run_in_executor(
                    None,
                    logger.log_queue.get
                )
                
                # WebSocketでメッセージを送信
                await ws.send_json({
                    "timestamp": log_record.created,
                    "message": log_record.getMessage()
                })
                
            except queue.Empty:
                # キューが空の場合は少し待機
                await asyncio.sleep(0.1)
                continue
                
            except Exception as e:
                logger.error(f"Error sending log: {e}")
                break
            
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        websocket = None 