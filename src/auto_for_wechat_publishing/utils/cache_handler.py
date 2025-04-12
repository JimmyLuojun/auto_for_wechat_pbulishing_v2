# src/auto_for_wechat_publishing/utils/cache_handler.py
import json
from pathlib import Path
from typing import Optional

CACHE_PATH = Path("data/cache/media_cache.json")

def load_cache() -> dict:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}

def save_cache(cache: dict) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache), encoding="utf-8")

def get_media_id_from_cache(image_path: str) -> Optional[str]:
    cache = load_cache()
    return cache.get(image_path)

def add_media_id_to_cache(image_path: str, media_id: str) -> None:
    cache = load_cache()
    cache[image_path] = media_id
    save_cache(cache)
