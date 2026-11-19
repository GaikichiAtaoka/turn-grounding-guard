# Temporal / Turn Grounding Guard

Bounded **Japanese** checks for a conversational assistant's current time,
recent turn order, and persistent-memory execution claims — with a reply
delivery gate that can request one correction and withhold an unresolved draft.

**[日本語 README](README_JA.md)** · **[AIへの組み込み手順](docs/INTEGRATION_JA.md)**

## What it does

An assistant may carry yesterday's bedtime farewell into a morning exchange,
claim that two nonadjacent replies were adjacent, or say it saved persistent
memory when no matching operation succeeded. This package checks a small,
explicit set of such conflicts against caller-supplied source records.

The public release covers **only** temporal/turn grounding and the execution
evidence needed by these checks. It does not include unfinished-message
classification, general memory retrieval, reflection, or a private agent runtime.

`guard_reply()` connects detection to the answer the host actually sends:

1. Check the complete candidate against immutable turn evidence and receipts.
2. If a supported conflict is found, optionally request **one** correction.
3. Recheck that correction against the **same** evidence and receipts.
4. Return `reply=None` when the correction fails, throws, or remains inconsistent.

The host must send only `result.reply` after this gate returns. Streaming or
displaying the original draft beforehand bypasses that guarantee.

## Status and license

- **v0.1.0 alpha**, source-available under **PolyForm Noncommercial 1.0.0**.
- Commercial use requires a separately agreed written license; see
  [COMMERCIAL-LICENSING.md](COMMERCIAL-LICENSING.md). Not OSI open source.
- Python 3.11+, standard library only, no runtime dependencies.
- No model downloads, network calls, telemetry, persistence, or automatic
  changes to conversation history. The optional correction callback belongs
  to the host application.

## Install and run

```bash
git clone https://github.com/GaikichiAtaoka/turn-grounding-guard.git
cd turn-grounding-guard
python -m pip install .
python -m unittest discover -s tests -v
python examples/agent_integration.py
turn-grounding-guard --input examples/synthetic_input.json
```

The offline example demonstrates `pass`, `corrected`, and `blocked`, and
asserts that the fake UI receives only the first two answers. Its correction
is scripted; this demonstrates wiring, not a model-quality benchmark.

The JSON CLI performs detection and delivery gating without a model callback.
The supplied input intentionally conflicts, so its expected exit status is
**2**, with `"status": "blocked"` and `"reply": null`.
Exit codes: 0 deliverable, 2 blocked, 1 invalid input.

## Minimal Python integration

```python
from turn_grounding_guard import build_turn_evidence, guard_reply

evidence = build_turn_evidence(
    [
        {"role": "user", "time": "2026-01-15T07:10:00+09:00",
         "content": "おはよう、仕事してくるね。", "message_id": "demo-u1"},
        {"role": "assistant", "time": "2026-01-15T07:10:04+09:00",
         "content": "行ってらっしゃい。", "message_id": "demo-a1"},
    ],
    user_message="うん、またあとでね。",
    reference="2026-01-15T07:45:00+09:00",
    turn_id="demo-current",
)

result = guard_reply(
    "またあとで。おやすみなさい。",
    evidence,
    # Replace with your host's bounded, text-only model call.
    regenerate=lambda request: "またあとでね。気をつけて。",
)
assert result.status == "corrected"
assert result.reply == "またあとでね。気をつけて。"
# Your application's only delivery point:
if result.reply is not None:
    print(result.reply)
```

For a real model, `correction_messages(request)` returns a system instruction
and a JSON data packet. Pass these to your existing text-completion call with
tools, memory writes, and action execution disabled. Set transport/token
timeouts in the host. The library makes at most one callback invocation; it
cannot enforce side-effect or wall-time constraints inside arbitrary Python
code supplied by the host.

## Supported checks

| Code | Evidence needed | Candidate conflict |
|---|---|---|
| `outdated_sleep_sendoff` | Local time 04:00–11:59, recent explicit work-departure statement, no subsequently recorded return/rest intent | A supported direct bedtime farewell |
| `invented_immediate_reply` | Current request asks to verify recent history; source-adjacent assistant reply was a departure sendoff | A supported claim that the morning greeting was immediately answered with a bedtime farewell |
| `unverified_memory_mutation` | No successful matching-turn `memory.write` / `memory.update` receipt | A supported completed persistent-memory save/update claim |
| `invalid_candidate` | Empty or oversized text | No deliverable candidate |

The morning check does **not** infer that every morning is work time. Night
shift returns, explicit rest intent, stale departure statements, unrelated
mornings, quotations, and common negations have separate handling. These are
bounded Japanese heuristics, not complete language understanding.

## Source and time contract

- Supply trusted `role`, `time`, `content`, and optional `message_id` fields
  in source order. `time` and `reference` must include UTC offsets. The
  reference's timezone determines the local daypart.
- The package examines at most `max_history * 3` input rows, retains at most
  `max_history` recent records (default 18), and uses a 3-hour history window.
  A work-departure statement expires after 90 minutes for the morning check.
- Naive/missing/stale/future record times are omitted, with an omission count.
  Omitted rows cannot establish an adjacent reply. Reversed valid timestamps
  are rejected rather than silently sorted.
- Text is never silently clipped into a new meaning. Limits are 4,000
  characters per history record, 16,000 for the current input, and 24,000 total
  source characters. Supply a smaller complete source window when necessary.
- A recorded intention is **not** proof that an action happened. Historical
  dialogue remains untrusted data in a correction prompt.

## Receipt contract

```python
from turn_grounding_guard import ExecutionReceipt, guard_reply

# Construct this only after your actual executor confirms success.
receipt = ExecutionReceipt(
    turn_id="demo-current", action="memory.write",
    ok=True, receipt_id="demo-write-1",
)
result = guard_reply("永続メモリを保存しました。", evidence, receipts=[receipt])
assert result.status == "pass"
```

Old-turn receipts, failed operations, and `memory.read` do not authorize a
save claim. String values such as `"false"` are rejected for `ok`. Receipt
objects and the turn projection are immutable, and the gate snapshots the
receipt sequence before correction. A callback cannot add a receipt to the
original list and thereby validate its new claim.

These objects are not cryptographic attestations. Their authenticity and
binding to actual operations are the host's responsibility. This narrow
check also does not prove that an updated record is the precise record
described in the answer. Use a more specific receipt contract if your
application needs record-level verification.

## Meaning of results

| Status | `reply` | Host behavior |
|---|---|---|
| `pass` | Original candidate | May deliver after these supported checks |
| `corrected` | Rechecked replacement | Deliver the replacement |
| `blocked` | `None` | Do not deliver the candidate; use your own transparent failure UI |

`issues` records the initial supported conflicts. `remaining_issues` records
the failed replacement's conflicts. Callback exceptions expose their class
name, not arbitrary exception text or the original draft.

Passing means that **these rules found no supported conflict**. It does not
validate every fact, person, date, quotation or paraphrase. An undetected
contradiction may still pass; a natural expression may be falsely flagged.
The same limitations apply after correction. The gate guarantees that a
**detected, still unresolved** candidate has no deliverable `reply` field.

## Privacy and release boundary

The examples, tests, IDs, dates, and dialogue are synthetic. The release
contains no private dialogue, persona, conversation database, credentials,
machine paths, model weights, or original application's Git history.
The package does not save inputs; your host's logs and model calls remain
your responsibility. See [source boundary](docs/SOURCE_BOUNDARY.md) and
[release verification](docs/RELEASE_VERIFICATION.md).
