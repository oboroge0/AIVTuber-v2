"""
ヘルパー関数モジュール
"""
import json
import os
from datetime import datetime
from typing import Any, Dict, List

def load_json_file(file_path: str) -> Dict[str, Any]:
    """
    JSONファイルを読み込む
    
    Args:
        file_path: JSONファイルのパス
        
    Returns:
        Dict[str, Any]: JSONデータ
    """
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json_file(file_path: str, data: Dict[str, Any]) -> None:
    """
    JSONファイルに保存する
    
    Args:
        file_path: JSONファイルのパス
        data: 保存するデータ
    """
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def create_backup(file_path: str, backup_dir: str) -> str:
    """
    ファイルのバックアップを作成する
    
    Args:
        file_path: バックアップするファイルのパス
        backup_dir: バックアップディレクトリ
        
    Returns:
        str: バックアップファイルのパス
    """
    if not os.path.exists(file_path):
        return ""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(
        backup_dir,
        f"{os.path.basename(file_path)}_{timestamp}.json"
    )
    
    os.makedirs(backup_dir, exist_ok=True)
    with open(file_path, 'r', encoding='utf-8') as src:
        with open(backup_path, 'w', encoding='utf-8') as dst:
            dst.write(src.read())
    
    return backup_path 