"""
VTSAnimatorの使用例
"""
import time
import sys
import os

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.vts_animator import VTSAnimator

def main():
    """メイン関数"""
    print("VTSアニメーターの例を開始します...")
    
    # アニメーターのインスタンスを作成
    animator = VTSAnimator()
    
    try:
        # アニメーターを開始
        animator.start()
        
        # ユーザーがCtrl+Cを押すまで待機
        print("Ctrl+Cを押すと停止します...")
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n停止リクエストを受信しました")
    finally:
        # アニメーターを停止
        animator.stop()
        print("プログラムを終了します")

if __name__ == "__main__":
    main() 