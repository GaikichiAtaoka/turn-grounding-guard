"""Offline JSON check. It never calls a model or writes conversation state."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys

from .core import ExecutionReceipt, build_turn_evidence, guard_reply


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Synthetic or caller-owned JSON input")
    args = parser.parse_args(argv)
    try:
        if args.input.stat().st_size > 256000:
            raise ValueError("input exceeds 256000 bytes")
        obj = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("input must be a JSON object")
        evidence = build_turn_evidence(
            obj.get("recent_dialogue", []), user_message=obj["user_message"],
            reference=obj["reference"], turn_id=obj["turn_id"],
        )
        receipts = [ExecutionReceipt(**row) for row in obj.get("receipts", [])]
        result = guard_reply(obj["reply"], evidence, receipts=receipts)
    except (ValueError, TypeError, KeyError, OSError) as exc:
        print(json.dumps({"status": "invalid", "error_type": type(exc).__name__}))
        return 1
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 2 if result.status == "blocked" else 0


if __name__ == "__main__":
    sys.exit(main())
