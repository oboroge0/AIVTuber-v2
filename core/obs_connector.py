"""
OBSコネクタモジュール
"""
import obsws_python
from utils.logger import get_logger
from core.config import Config

logger = get_logger(__name__)

class OBSConnector:
    """OBSコネクター"""
    
    def __init__(self):
        """初期化"""
        self.ws = obsws_python.ReqClient(
            host=Config.OBS_WS_HOST,
            port=Config.OBS_WS_PORT,
            password=Config.OBS_WS_PASSWORD
        )
    
    def set_answer(self, text: str) -> None:
        """
        回答テキストを設定する
        
        Args:
            text: 設定するテキスト
        """
        try:
            with self.ws:
                # "Answer"テキストソースを更新
                self.ws.set_input_settings(
                    "Answer",
                    {"text": text},
                    True
                )
        except Exception as e:
            logger.error(f"Error setting answer text: {e}")
            raise
    
    def set_chat_url(self, video_id: str) -> None:
        """
        チャットURLを設定する
        
        Args:
            video_id: 動画ID
        """
        try:
            with self.ws:
                # "コメント欄"ブラウザソースのURLを更新
                chat_url = f"https://www.youtube.com/live_chat?v={video_id}&embed_domain=localhost"
                self.ws.set_input_settings(
                    "コメント欄",
                    {"url": chat_url},
                    True
                )
        except Exception as e:
            logger.error(f"Error setting chat URL: {e}")
            raise 