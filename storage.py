import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


def _storage_path() -> Path:
    return Path(os.getenv("STORAGE_FILE", "data/grades.json"))


def _load() -> dict:
    path = _storage_path()
    if not path.exists():
        return {"seen": [], "last_check": None}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: dict) -> None:
    path = _storage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_seen_uids() -> Set[str]:
    return set(_load().get("seen", []))


def mark_seen(uids: List[str]) -> None:
    data = _load()
    seen = set(data.get("seen", []))
    seen.update(uids)
    data["seen"] = sorted(seen)
    data["last_check"] = datetime.now().isoformat()
    _save(data)
    logger.debug("Marked %d UIDs as seen (total: %d)", len(uids), len(seen))


def get_last_check() -> Optional[str]:
    return _load().get("last_check")


def is_first_run() -> bool:
    data = _load()
    return not data.get("seen") and data.get("last_check") is None
