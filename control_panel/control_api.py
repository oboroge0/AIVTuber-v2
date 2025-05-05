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

@app.post("/start")
async def start_stream(request: StartRequest):
    """配信を開始する"""
    try:
        await controller.start(request.video_id)
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
        "is_comment_processing": controller.is_comment_processing()
    }

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