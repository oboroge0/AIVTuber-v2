"""
Streamlitコントロールパネル
"""
import streamlit as st
import requests
import json
import os
import sys
from datetime import datetime, timezone

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# APIサーバーのアドレスを環境変数から取得
API_HOST = os.environ.get("AIVTUBER_API_HOST", "localhost")
API_PORT = os.environ.get("AIVTUBER_API_PORT", "8000")
API_URL = f"http://{API_HOST}:{API_PORT}"

# ページ設定
st.set_page_config(
    page_title="AIVTuber Control Panel",
    page_icon="🎥",
    layout="wide"
)

# タイトル
st.title("AIVTuber Control Panel")

# APIサーバー情報を表示
st.sidebar.info(f"APIサーバー: {API_URL}")

# サイドバー
with st.sidebar:
    st.header("配信制御")
    
    # テーマ設定
    st.header("配信テーマ")
    current_theme = st.text_input("現在の配信テーマ", value=st.session_state.get("current_theme", ""))
    if st.button("テーマを設定"):
        if current_theme:
            response = requests.post(
                f"{API_URL}/set_theme",
                json={"theme": current_theme}
            )
            if response.status_code == 200:
                st.success("テーマを設定しました")
                st.session_state.current_theme = current_theme
            else:
                st.error(f"エラー: {response.text}")
        else:
            st.warning("テーマを入力してください")
    
    # チャンネルID選択
    channel_options = {
        "おぼろげ": "UCF3rtSDBs-2VmYSiEVUf4Qw",
        "天知レイ": "UCgiYsOd1wZ2mVR6g0tQIwrw"
    }
    selected_channel = st.selectbox("YouTube チャンネル", options=list(channel_options.keys()))
    channel_id = channel_options[selected_channel]
    
    # 配信リスト取得ボタン
    if st.button("配信リストを取得"):
        from control_panel.youtube_api import get_live_streams
        
        # 配信リストを取得（配信中と配信予定の両方を取得）
        live_streams = get_live_streams(channel_id, include_upcoming=True)
        
        if live_streams:
            # 配信リストをセッションステートに保存
            st.session_state.live_streams = live_streams
            
            # 配信リストを表示
            stream_options = {}
            now = datetime.now(timezone.utc)
            for stream in live_streams:
                # 配信予定の場合は開始時間を表示
                if stream.startTime > now:
                    time_str = stream.startTime.strftime("%Y-%m-%d %H:%M")
                    stream_options[f"配信予定：{stream.title} (開始: {time_str})"] = stream.id
                else:
                    stream_options[f"配信中：{stream.title}"] = stream.id
            
            selected_stream = st.selectbox("配信を選択", options=list(stream_options.keys()))
            
            # 選択した配信のvideo_idを入力欄に反映
            if selected_stream:
                st.session_state.video_id = stream_options[selected_stream]
        else:
            if channel_id:
                st.warning(f"チャンネルID {channel_id} の配信が見つかりませんでした")
            else:
                st.warning("配信が見つかりませんでした")
    
    # 配信開始
    video_id = st.text_input("YouTube Live ID", value=st.session_state.get("video_id", ""))
    if st.button("配信開始"):
        if video_id:
            response = requests.post(
                f"{API_URL}/start",
                json={"video_id": video_id}
            )
            if response.status_code == 200:
                st.success("配信を開始しました")
            else:
                st.error(f"エラー: {response.text}")
        else:
            st.warning("YouTube Live IDを入力してください")
    
    # 配信停止
    if st.button("配信停止"):
        response = requests.post(f"{API_URL}/stop")
        if response.status_code == 200:
            st.success("配信を停止しました")
        else:
            st.error(f"エラー: {response.text}")
    
    # 手動発話
    st.header("手動発話")
    manual_text = st.text_area("発話テキスト")
    if st.button("発話"):
        if manual_text:
            response = requests.post(
                f"{API_URL}/speak",
                json={"text": manual_text}
            )
            if response.status_code == 200:
                st.success("発話を開始しました")
            else:
                st.error(f"エラー: {response.text}")
        else:
            st.warning("発話テキストを入力してください")

# メインコンテンツ
col1, col2 = st.columns(2)

# 配信情報
with col1:
    st.header("配信情報")
    try:
        response = requests.get(f"{API_URL}/status")
        if response.status_code == 200:
            status = response.json()
            st.write(f"配信状態: {'配信中' if status['is_running'] else '停止中'}")
            if status['current_video_id']:
                st.write(f"現在の配信: {status['current_video_id']}")
        else:
            st.error("ステータス取得エラー")
    except:
        st.error("サーバーに接続できません")

# ログ表示
with col2:
    st.header("ログ")
    log_placeholder = st.empty()
    
    # WebSocketでログを取得
    import websockets
    import asyncio
    
    async def receive_logs():
        try:
            async with websockets.connect(f"ws://{API_HOST}:{API_PORT}/logs") as websocket:
                while True:
                    try:
                        log = await websocket.recv()
                        log_data = json.loads(log)
                        timestamp = datetime.fromtimestamp(log_data['timestamp'])
                        log_placeholder.write(f"{timestamp.strftime('%H:%M:%S')} - {log_data['message']}")
                    except websockets.exceptions.ConnectionClosed:
                        log_placeholder.error("ログサーバーとの接続が切断されました")
                        break
                    except Exception as e:
                        log_placeholder.error(f"ログの受信中にエラーが発生しました: {e}")
                        break
        except Exception as e:
            log_placeholder.error(f"ログサーバーに接続できません: {e}")
    
    # WebSocketの接続を開始
    asyncio.run(receive_logs()) 