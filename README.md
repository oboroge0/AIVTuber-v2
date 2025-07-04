# AIVTuber v2

AIVTuber v2は、YouTubeライブ配信のコメントにAIが応答するインタラクティブなVTuberシステムです。HippoRAGによる長期記憶機能を搭載し、より自然で継続的な会話が可能になりました。

## 主な機能

- **リアルタイムコメント応答**: YouTubeライブチャットを監視し、AIが自動応答
- **高度なコメントフィルタリング**: スコアリングアルゴリズムによる適切なコメント選択
- **長期記憶機能**: HippoRAGを使用した会話履歴の長期保存と文脈理解
- **音声合成**: Style-BERT-VITS 2による高品質な音声生成
- **キャラクターアニメーション**: VTube Studioとの連携による生き生きとした動き
- **配信制御**: OBS Studioとの統合による字幕表示とシーン管理
- **独り言機能**: コメントがない時の継続的な会話生成
- **Webベースコントロールパネル**: 直感的な操作インターフェース

## システム要件

### 必須要件
- Python 3.10以上
- CUDA対応GPU（推奨）
- 8GB以上のRAM

### 必要なAPIキー
- OpenAI APIキー（GPT-4アクセス）
- YouTube Data APIキー

### 外部ソフトウェア
- OBS Studio v28以上（obs-websocketプラグイン有効化）
- VTube Studio
- Style-BERT-VITS 2サーバー

## インストール

### 1. リポジトリをクローン
```bash
git clone https://github.com/yourusername/AIVTuber-v2.git
cd AIVTuber-v2
```

### 2. 依存関係をインストール
```bash
pip install -r requirements.txt
```

### 3. 環境変数を設定
`.env`ファイルを作成し、以下の設定を記入：
```env
# 必須設定
OPENAI_API_KEY=your_openai_api_key_here
YOUTUBE_API_KEY=your_youtube_api_key_here
OBS_WS_PASSWORD=your_obs_password_here

# オプション設定
STYLE_BERT_VITS2_HOST=localhost
STYLE_BERT_VITS2_PORT=50021
VTS_WS_PORT=8001
USE_CUDA=true
```

### 4. 必要なディレクトリを作成
```bash
python -c "from core.config import Config; Config.validate()"
```

## 使用方法

### クイックスタート
最も簡単な起動方法：
```bash
python run.py
```
これにより、APIサーバーとコントロールパネルが自動的に起動します。

### 手動起動（詳細設定が必要な場合）

#### 1. 外部アプリケーションの準備

1. **OBS Studio**を起動し、以下のソースを設定：
   - "Answer"（テキストソース）: AIの応答を表示
   - "コメント欄"（ブラウザソース）: YouTubeコメントを表示

2. **VTube Studio**を起動し、APIを有効化

3. **Style-BERT-VITS 2**サーバーを起動

#### 2. AIVTuberを起動

```bash
# APIサーバーを起動
uvicorn control_panel.control_api:app --host localhost --port 8000

# 別のターミナルでコントロールパネルを起動
streamlit run control_panel/app.py
```

#### 3. 配信開始

1. ブラウザで `http://localhost:8501` にアクセス
2. YouTube配信URLを入力
3. 「配信開始」ボタンをクリック

## 高度な機能

### HippoRAG長期記憶
```python
from memory.hipporag_memory import VTuberMemory

# GPUを使用した高速処理
memory = VTuberMemory(
    model_name="cl-nagoya/sup-simcse-ja-large",
    use_gpu=True
)

# 記憶の保存
memory.save()

# 記憶の検索
results = memory.search("以前話した内容", top_k=5)
```

### VTSAnimator（キャラクターアニメーション）
```python
from core.vts_animator import VTSAnimator

# アニメーターの設定
animator = VTSAnimator()
animator.start()

# カスタムアニメーションの追加
animator.trigger_hotkey("custom_expression_1")
```

### カスタムプロンプト
`prompts/`ディレクトリに独自のプロンプトファイルを追加：
```
prompts/my_character.txt
```

## プロジェクト構造

```
AIVTuber-v2/
├── core/               # コアシステムモジュール
│   ├── controller.py   # メインコントローラー
│   ├── comment_listener.py  # YouTubeコメント監視
│   ├── responder.py    # AI応答生成
│   └── speech.py       # 音声合成
├── memory/             # HippoRAG記憶システム
├── control_panel/      # Webコントロールパネル
├── prompts/            # キャラクタープロンプト
├── storage/            # データ保存
└── run.py             # 起動スクリプト
```

## トラブルシューティング

### よくある問題

1. **音声が再生されない**
   - Style-BERT-VITS 2サーバーが起動しているか確認
   - ポート設定が正しいか確認

2. **コメントが取得できない**
   - YouTube APIキーが正しく設定されているか確認
   - APIの利用制限に達していないか確認

3. **メモリ不足エラー**
   - `USE_CUDA=false`に設定してCPUモードで実行
   - バッチサイズを小さくする

### ログの確認
```bash
# リアルタイムログの表示
tail -f logs/aivtuber.log
```

## 開発者向け情報

### テストの実行
```bash
pytest tests/
```

### コントリビューション
プルリクエストを歓迎します！以下のガイドラインに従ってください：
1. フォークしてフィーチャーブランチを作成
2. コミットメッセージは明確に
3. テストを追加
4. プルリクエストを送信

## ライセンス

MIT License 