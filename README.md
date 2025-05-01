# AIVTuber

AIVTuberは、YouTubeライブ配信のコメントに応答するAI VTuberシステムです。

## 機能

- YouTubeライブチャットのリアルタイム監視
- コメントのスコアリングとフィルタリング
- GPT-4による応答生成
- Style-BERT-VITS 2による音声合成
- VTube Studioによるアニメーション
- OBSとの連携
- Streamlit + FastAPIによるコントロールパネル
- VTube Studioのホットキーをランダムにトリガーする機能

## 必要条件

- Python 3.10以上
- OpenAI APIキー
- YouTube Data APIキー
- OBS Studio（obs-websocketプラグイン）
- VTube Studio
- Style-BERT-VITS 2

## インストール

1. リポジトリをクローン
```bash
git clone https://github.com/yourusername/aivtuber_v2.git
cd aivtuber_v2
```

2. 依存関係をインストール
```bash
pip install -r requirements.txt
```

3. 環境変数を設定
`.env`ファイルを作成し、必要な設定を記入：
```env
OPENAI_API_KEY=your_openai_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
OBS_WS_PASSWORD=your_obs_password_here
```

## 使用方法

1. OBS Studioを起動し、以下のソースを追加：
   - "Answer"（テキストソース）
   - "コメント欄"（ブラウザソース）

2. VTube Studioを起動

3. Style-BERT-VITS 2サーバーを起動

4. コントロールパネルを起動
```bash
streamlit run control_panel/app.py
```

5. APIサーバーを起動
```bash
uvicorn control_panel.control_api:app --host localhost --port 8000
```

6. コントロールパネルで配信を開始

## VTSAnimatorの使用方法

VTSAnimatorは、VTube Studioのホットキーをランダムにトリガーする機能を提供します。

```python
from core.vts_animator import VTSAnimator

# アニメーターのインスタンスを作成
animator = VTSAnimator()

# アニメーターを開始
animator.start()

# アニメーターを停止
animator.stop()
```

サンプルスクリプトを実行するには：

```bash
python examples/vts_animator_example.py
```

## ライセンス

MIT License 