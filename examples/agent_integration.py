"""Run all three delivery outcomes with entirely synthetic data, offline.

The scripted correction demonstrates host wiring, not model effectiveness.
No draft is sent to the fake UI before guard_reply completes.
"""
from dataclasses import asdict
import json

from turn_grounding_guard import build_turn_evidence, guard_reply


def run_demo() -> dict:
    evidence = build_turn_evidence([
        {"role": "user", "time": "2026-01-15T07:10:00+09:00",
         "content": "おはよう、仕事してくるね。", "message_id": "demo-u1"},
        {"role": "assistant", "time": "2026-01-15T07:10:04+09:00",
         "content": "行ってらっしゃい。", "message_id": "demo-a1"},
    ], user_message="うん、またあとでね。", reference="2026-01-15T07:45:00+09:00",
        turn_id="demo-current")
    delivered: list[str] = []
    results = []
    candidates = [
        ("またあとでね。", None),
        ("またあとで。おやすみなさい。", lambda request: "またあとでね。気をつけて。"),
        ("おやすみなさい。", lambda request: "おやすみなさい。"),
    ]
    for draft, callback in candidates:
        result = guard_reply(draft, evidence, regenerate=callback)
        if result.reply is not None:
            delivered.append(result.reply)  # The sole UI-delivery point.
        results.append(asdict(result))
    assert [r["status"] for r in results] == ["pass", "corrected", "blocked"]
    assert len(delivered) == 2
    assert all("おやすみ" not in text for text in delivered)
    return {"results": results, "delivered_to_ui": delivered}


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2))
