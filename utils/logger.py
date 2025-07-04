"""
ロギングユーティリティモジュール
"""
import logging
import queue
import threading
from typing import Optional

class QueueHandler(logging.Handler):
    """キューを使用したログハンドラ"""
    
    def __init__(self, queue: queue.Queue):
        super().__init__()
        self.queue = queue
    
    def emit(self, record):
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            pass

def get_logger(name: str) -> logging.Logger:
    """
    ロガーを取得する
    
    Args:
        name: ロガー名
        
    Returns:
        logging.Logger: 設定済みのロガー
    """
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # コンソールハンドラ
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        
        # キューハンドラ（WebSocket用）
        log_queue = queue.Queue()
        queue_handler = QueueHandler(log_queue)
        queue_handler.setLevel(logging.INFO)
        queue_handler.setFormatter(formatter)
        logger.addHandler(queue_handler)
        
        # キューをグローバル変数として保存
        setattr(logger, 'log_queue', log_queue)
    
    return logger 