"""
OBSコネクタモジュール
"""
import obsws_python as obs
from utils.logger import get_logger
from core.config import Config

logger = get_logger(__name__)

class OBSConnector:
    """OBSコネクター"""
    
    def __init__(self):
        """初期化"""
        host = Config.OBS_WS_HOST
        port = Config.OBS_WS_PORT
        password = Config.OBS_WS_PASSWORD

        if not host or not port or not password:
            raise ValueError('OBSの設定が正しくありません')

        self.ws = obs.ReqClient(host=host, port=port, password=password)
        logger.info("OBSに接続しました")
    
    def set_answer(self, text: str) -> None:
        """
        回答テキストを設定する
        
        Args:
            text: 設定するテキスト
        """
        try:
            self.ws.set_input_settings(
                name="Answer",
                settings={'text': text},
                overlay=True
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
            chat_url = f"https://studio.youtube.com/live_chat?is_popout=1&v={video_id}"
            self.ws.set_input_settings(
                name="コメント欄",
                settings={'url': chat_url},
                overlay=True
            )
        except Exception as e:
            logger.error(f"Error setting chat URL: {e}")
            raise 