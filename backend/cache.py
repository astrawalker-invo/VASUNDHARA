"""Two-layer cache: in-memory LRU + JSON files on disk. Real API responses only.
Callers must never put fabricated values here. (Redis layer: add later if needed.)"""
import json, hashlib, time, os, threading
from collections import OrderedDict
from pathlib import Path

CACHE_DIR = Path(os.getenv("CACHE_DIR", ".cache")); CACHE_DIR.mkdir(exist_ok=True)
_LRU: "OrderedDict[str, tuple[float, dict]]" = OrderedDict(); _MAX = 256; _lock = threading.Lock()

def key(endpoint: str, lat: float, lon: float, decimals: int, **params) -> str:
    raw = f"{endpoint}|{round(lat, decimals)}|{round(lon, decimals)}|{sorted(params.items())}"
    return hashlib.sha1(raw.encode()).hexdigest()

def get(k: str, ttl: float):
    now = time.time()
    with _lock:
        if k in _LRU and now - _LRU[k][0] < ttl:
            _LRU.move_to_end(k); return _LRU[k][1]
    f = CACHE_DIR / f"{k}.json"
    if f.exists() and now - f.stat().st_mtime < ttl:
        val = json.loads(f.read_text()); put_mem(k, val); return val
    return None

def put_mem(k, val):
    with _lock:
        _LRU[k] = (time.time(), val); _LRU.move_to_end(k)
        while len(_LRU) > _MAX: _LRU.popitem(last=False)

def put(k: str, val: dict):
    put_mem(k, val); (CACHE_DIR / f"{k}.json").write_text(json.dumps(val))

TTL_HISTORY = 30 * 86400   # long history rarely changes
TTL_RECENT = 6 * 3600      # recent period / market prices
