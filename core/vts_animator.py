"""
VTubeStudioアニメーター
ランダムにアニメーションをトリガーする機能を提供します
"""
import asyncio
import json
import random
import threading
import websockets
from typing import List, Dict, Any, Optional

from utils.logger import get_logger
from core.config import Config

logger = get_logger(__name__)

class VTSAnimator:
    """VTubeStudioアニメーター"""
    
    def __init__(self, ws_uri: Optional[str] = None):
        """
        初期化
        
        Args:
            ws_uri: WebSocket URI（オプション）
        """
        self.ws_uri = ws_uri or f"ws://localhost:{Config.VTS_WS_PORT}"
        self.plugin_name = "AIVTuber"
        self.plugin_developer = "AIVTuber"
        self._running = False
        self._thread = None
        self._hotkeys: List[Dict[str, Any]] = []
    
    async def _request_token(self, ws) -> Optional[str]:
        """
        認証トークンをリクエスト
        
        Args:
            ws: WebSocket接続
            
        Returns:
            認証トークン
        """
        req = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "TokenRequestID",
            "messageType": "AuthenticationTokenRequest",
            "data": {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_developer
            }
        }
        await ws.send(json.dumps(req))
        resp = json.loads(await ws.recv())
        return resp["data"].get("authenticationToken")
    
    async def _authenticate(self, ws, token: str) -> bool:
        """
        認証を実行
        
        Args:
            ws: WebSocket接続
            token: 認証トークン
            
        Returns:
            認証成功したかどうか
        """
        req = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "AuthenticationRequestID",
            "messageType": "AuthenticationRequest",
            "data": {
                "pluginName": self.plugin_name,
                "pluginDeveloper": self.plugin_developer,
                "authenticationToken": token
            }
        }
        await ws.send(json.dumps(req))
        resp = json.loads(await ws.recv())
        return resp["data"].get("authenticated", False)
    
    async def _get_hotkeys(self, ws) -> List[Dict[str, Any]]:
        """
        ホットキー一覧を取得
        
        Args:
            ws: WebSocket接続
            
        Returns:
            ホットキー一覧
        """
        req = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "GetHotkeysRequestID",
            "messageType": "HotkeysInCurrentModelRequest"
        }
        await ws.send(json.dumps(req))
        resp = json.loads(await ws.recv())
        return resp["data"]["availableHotkeys"]
    
    async def _trigger_hotkey(self, ws, hotkey_id: str) -> None:
        """
        ホットキーをトリガー
        
        Args:
            ws: WebSocket接続
            hotkey_id: ホットキーID
        """
        req = {
            "apiName": "VTubeStudioPublicAPI",
            "apiVersion": "1.0",
            "requestID": "TriggerHotkeyRequestID",
            "messageType": "HotkeyTriggerRequest",
            "data": {
                "hotkeyID": hotkey_id
            }
        }
        await ws.send(json.dumps(req))
        await ws.recv()
    
    async def _run(self) -> None:
        """メインループ"""
        try:
            async with websockets.connect(self.ws_uri) as ws:
                token = await self._request_token(ws)
                if not token:
                    logger.error("認証トークン取得失敗")
                    return
                
                authenticated = await self._authenticate(ws, token)
                if not authenticated:
                    logger.error("認証失敗")
                    return
                
                logger.info("認証成功")
                self._hotkeys = await self._get_hotkeys(ws)
                
                if not self._hotkeys:
                    logger.error("ホットキーが見つかりません")
                    return
                
                logger.info("ランダムにアニメーションをトリガーします。stop()で停止")
                
                while self._running:
                    hotkey = random.choice(self._hotkeys)
                    logger.info(f"トリガー: {hotkey['name']} ({hotkey['hotkeyID']})")
                    await self._trigger_hotkey(ws, hotkey['hotkeyID'])
                    await asyncio.sleep(random.uniform(30, 60))
        except Exception as e:
            logger.error(f"VTSアニメーターエラー: {e}")
    
    def start(self) -> None:
        """アニメーターを開始"""
        if self._running:
            logger.warning("すでに実行中です")
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._start_async_loop, daemon=True)
        self._thread.start()
        logger.info("VTSアニメーターを開始しました")
    
    def _start_async_loop(self) -> None:
        """非同期ループを開始"""
        asyncio.run(self._run())
    
    def stop(self) -> None:
        """アニメーターを停止"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None
        logger.info("VTSアニメーションの自動トリガーを停止しました") 