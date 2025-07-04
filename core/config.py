"""
設定管理モジュール
"""
import os
from dotenv import load_dotenv

# 環境変数の読み込み
load_dotenv()

class Config:
    """設定管理クラス"""
    
    # API Keys
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
    
    # OBS WebSocket
    OBS_WS_HOST = os.getenv("OBS_WS_HOST", "localhost")
    OBS_WS_PORT = int(os.getenv("OBS_WS_PORT", "4455"))
    OBS_WS_PASSWORD = os.getenv("OBS_WS_PASSWORD")
    
    # Style-BERT-VITS 2
    STYLE_BERT_VITS2_HOST = os.getenv("STYLE_BERT_VITS2_HOST", "localhost")
    STYLE_BERT_VITS2_PORT = int(os.getenv("STYLE_BERT_VITS2_PORT", "50021"))
    
    # VTube Studio
    VTS_WS_PORT = int(os.getenv("VTS_WS_PORT", "8001"))
    
    # Server Settings
    CONTROL_API_HOST = os.getenv("CONTROL_API_HOST", "localhost")
    CONTROL_API_PORT = int(os.getenv("CONTROL_API_PORT", "8000"))
    STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))
    
    # Storage Paths
    STORAGE_DIR = "storage"
    HISTORY_DIR = os.path.join(STORAGE_DIR, "history")
    BACKUPS_DIR = os.path.join(HISTORY_DIR, "backups")
    HIPPORAG_DIR = os.path.join(STORAGE_DIR, "hipporag")
    VOICE_MODEL_DIR = os.path.join(STORAGE_DIR, "voice_model/Anneli")
    PROMPTS_DIR = "prompts"
    
    # Prompt Settings
    DEFAULT_PROMPT_FILE = "comment_mode.txt"
    MAX_HISTORY_TURNS = 1000
    
    # Comment Scoring
    THRESHOLD = 0.0  # コメントスコアリングの閾値
    
    # Voice Model Settings
    VOICE_MODEL = {
        "bert": {
            "model": "ku-nlp/deberta-v2-large-japanese-char-wwm",
            "tokenizer": "ku-nlp/deberta-v2-large-japanese-char-wwm"
        },
        "model": {
            "file": "Anneli_e116_s32000.safetensors",
            "config": "config.json",
            "style_vectors": "style_vectors.npy",
            "device": "cuda" if os.getenv("USE_CUDA", "true").lower() == "true" else "cpu"
        }
    }
    
    # 音声認識設定
    VOICE_RECOGNITION = {
        "enabled": os.getenv("VOICE_RECOGNITION_ENABLED", "false").lower() == "true",
        "language": os.getenv("VOICE_LANGUAGE", "ja-JP"),
        "sample_rate": int(os.getenv("VOICE_SAMPLE_RATE", "16000")),
        "chunk_size": int(os.getenv("VOICE_CHUNK_SIZE", "1024")),
        "energy_threshold": int(os.getenv("VOICE_ENERGY_THRESHOLD", "4000")),
        "mic_device_index": None,  # None for default device
        "google_cloud_credentials": os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    }
    
    # 動作モード設定
    OPERATION_MODE = os.getenv("OPERATION_MODE", "chat")  # "chat", "voice", "hybrid"
    
    @classmethod
    def validate(cls):
        """設定の検証"""
        required_vars = [
            "OPENAI_API_KEY",
            "YOUTUBE_API_KEY",
            "OBS_WS_PASSWORD"
        ]
        
        missing_vars = [var for var in required_vars if not getattr(cls, var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # 音声認識が有効な場合の追加検証
        if cls.VOICE_RECOGNITION["enabled"]:
            if not cls.VOICE_RECOGNITION["google_cloud_credentials"]:
                raise ValueError("GOOGLE_APPLICATION_CREDENTIALS is required when voice recognition is enabled")
        
        # ディレクトリの作成
        os.makedirs(cls.HISTORY_DIR, exist_ok=True)
        os.makedirs(cls.BACKUPS_DIR, exist_ok=True)
        os.makedirs(cls.HIPPORAG_DIR, exist_ok=True)
        os.makedirs(cls.VOICE_MODEL_DIR, exist_ok=True)
        os.makedirs(cls.PROMPTS_DIR, exist_ok=True) 