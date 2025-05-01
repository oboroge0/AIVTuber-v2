"""
AIVTuber起動スクリプト
"""
import os
import sys
import subprocess
import time
import signal
import atexit

def start_api_server():
    """APIサーバーを起動する"""
    api_cmd = ["uvicorn", "control_panel.control_api:app", "--host", "localhost", "--port", "8000"]
    api_process = subprocess.Popen(api_cmd)
    print("APIサーバーを起動しました")
    return api_process

def start_control_panel():
    """コントロールパネルを起動する"""
    panel_cmd = ["streamlit", "run", "control_panel/app.py"]
    panel_process = subprocess.Popen(panel_cmd)
    print("コントロールパネルを起動しました")
    return panel_process

def cleanup(api_process, panel_process):
    """プロセスを終了する"""
    print("プロセスを終了します...")
    api_process.terminate()
    panel_process.terminate()
    api_process.wait()
    panel_process.wait()
    print("プロセスを終了しました")

def main():
    """メイン関数"""
    # APIサーバーを起動
    api_process = start_api_server()
    
    # APIサーバーの起動を待つ
    time.sleep(2)
    
    # コントロールパネルを起動
    panel_process = start_control_panel()
    
    # 終了時の処理を登録
    atexit.register(cleanup, api_process, panel_process)
    
    # シグナルハンドラを設定
    def signal_handler(sig, frame):
        print("終了シグナルを受信しました")
        cleanup(api_process, panel_process)
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # プロセスが終了するまで待機
    try:
        api_process.wait()
    except KeyboardInterrupt:
        pass
    finally:
        cleanup(api_process, panel_process)

if __name__ == "__main__":
    main() 