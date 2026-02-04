import json
from pathlib import Path
from typing import Any


def load_ruleset(path: str | None = None) -> dict[str, Any]:
    if path is None:
        path = Path(__file__).with_name("ruleset_v1.json")
    else:
        path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
