"""HippoRAG ラッパーモジュール"""

from typing import List, Dict
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
import os


@dataclass
class Document:
    page_content: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_content": self.page_content,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Document':
        return cls(
            page_content=data["page_content"],
            metadata=data["metadata"]
        )


class VTuberMemory:
    """AIVTuber 用の HippoRAG ラッパー。"""

    def __init__(self, model_name: str = "cl-nagoya/sup-simcse-ja-large", use_gpu: bool = False, 
                 persist_dir: str = "memory_data"):
        device = "cuda" if use_gpu else "cpu"
        self.embed_model = SentenceTransformer(model_name, device=device)
        self.documents: List[Document] = []
        self.embeddings: Optional[np.ndarray] = None
        self.index: Optional[faiss.IndexFlatL2] = None
        
        # 永続化用のディレクトリ設定
        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.documents_file = self.persist_dir / "documents.json"
        self.embeddings_file = self.persist_dir / "embeddings.npy"
        self.index_file = self.persist_dir / "index.faiss"
        
        # 保存済みデータの読み込み
        self._load_persisted_data()

    def _load_persisted_data(self):
        """保存済みデータを読み込む"""
        if self.documents_file.exists():
            with open(self.documents_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.documents = [Document.from_dict(d) for d in data]
        
        if self.embeddings_file.exists():
            self.embeddings = np.load(self.embeddings_file)
            
        if self.index_file.exists():
            self.index = faiss.read_index(str(self.index_file))
        elif self.embeddings is not None:
            dimension = self.embeddings.shape[1]
            self.index = faiss.IndexFlatL2(dimension)
            self.index.add(self.embeddings)

    def _persist_data(self):
        """データを永続化"""
        # ドキュメントの保存
        with open(self.documents_file, "w", encoding="utf-8") as f:
            json.dump([doc.to_dict() for doc in self.documents], f, ensure_ascii=False, indent=2)
        
        # 埋め込みの保存
        if self.embeddings is not None:
            np.save(self.embeddings_file, self.embeddings)
        
        # FAISSインデックスの保存
        if self.index is not None:
            faiss.write_index(self.index, str(self.index_file))

    def _update_index(self):
        """FAISSインデックスを更新"""
        if not self.documents:
            return

        # 埋め込みを計算
        texts = [doc.page_content for doc in self.documents]
        self.embeddings = self.embed_model.encode(texts, convert_to_numpy=True)
        
        # FAISSインデックスを作成
        dimension = self.embeddings.shape[1]
        self.index = faiss.IndexFlatL2(dimension)
        self.index.add(self.embeddings)
        
        # データを永続化
        self._persist_data()

    def add(self, text: str, meta: Dict | None = None) -> None:
        """会話やイベントを記憶に追加"""
        self.documents.append(Document(page_content=text, metadata=meta or {}))
        self._update_index()

    def retrieve(self, query: str, top_k: int = 5) -> List[str]:
        """質問に関連するコンテキストを RAG で取得"""
        if not self.documents or self.index is None:
            return []

        # クエリの埋め込みを計算
        query_embedding = self.embed_model.encode([query], convert_to_numpy=True)
        
        # 類似度検索
        distances, indices = self.index.search(query_embedding, top_k)
        
        # 結果を返す
        return [self.documents[i].page_content for i in indices[0]] 