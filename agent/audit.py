"""Append-only record of every tool call and what happened to it."""

import json
import time

from .config import CONFIG


def record(tool, args, outcome, reason=""):
    """outcome: allowed | approved | denied | error. Never raises."""
    try:
        line = {
            "time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tool": tool,
            "args": str(args)[:500],
            "outcome": outcome,
            "reason": reason,
        }
        path = CONFIG.runtime_dir / "audit.jsonl"
        if path.exists() and path.stat().st_size > 5_000_000:  # keep one old copy, ~5 MB each
            path.replace(path.with_name("audit.old.jsonl"))
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(line, ensure_ascii=False) + "\n")
    except Exception:  # noqa: BLE001
        pass
