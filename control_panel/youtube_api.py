"""
YouTube APIモジュール
"""
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from typing import List, Optional
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.models import Video
from utils.logger import get_logger
from core.config import Config

logger = get_logger(__name__)

def get_live_streams(channel_id: Optional[str] = None, include_upcoming: bool = False) -> List[Video]:
    """
    ライブ配信中の動画を取得する
    
    Args:
        channel_id: チャンネルID（オプション）。指定すると、そのチャンネルのライブ配信のみを取得
        include_upcoming: 配信予定の動画も含めるかどうか
    
    Returns:
        List[Video]: 動画のリスト
    """
    try:
        youtube = build('youtube', 'v3', developerKey=Config.YOUTUBE_API_KEY)
        
        # ライブ配信を検索
        search_params = {
            "part": "snippet",
            "type": "video",
            "maxResults": 10
        }
        
        # 配信予定を含めるかどうかで検索条件を変更
        if include_upcoming:
            search_params["eventType"] = "upcoming"
        else:
            search_params["eventType"] = "live"
        
        # チャンネルIDが指定されている場合は、そのチャンネルのライブ配信のみを取得
        if channel_id:
            search_params["channelId"] = channel_id
            
        request = youtube.search().list(**search_params)
        response = request.execute()
        
        # 動画情報を取得
        videos = []
        for item in response.get('items', []):
            video_id = item['id']['videoId']
            title = item['snippet']['title']
            published_at = datetime.fromisoformat(
                item['snippet']['publishedAt'].replace('Z', '+00:00')
            )
            
            # 配信予定の場合は開始時間を取得
            start_time = published_at
            if include_upcoming:
                # 配信予定の場合は、scheduledStartTimeを取得
                try:
                    video_details = youtube.videos().list(
                        part="liveStreamingDetails",
                        id=video_id
                    ).execute()
                    
                    if video_details.get('items'):
                        scheduled_start = video_details['items'][0].get('liveStreamingDetails', {}).get('scheduledStartTime')
                        if scheduled_start:
                            start_time = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00'))
                except Exception as e:
                    logger.warning(f"Failed to get scheduled start time for video {video_id}: {e}")
            
            videos.append(Video(
                id=video_id,
                title=title,
                startTime=start_time
            ))
        
        return videos
        
    except Exception as e:
        logger.error(f"Error fetching live streams: {e}")
        return [] 