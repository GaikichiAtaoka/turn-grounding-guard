# Release verification — 0.1.0

Date: **2026-11-20**. Scope: standalone package, synthetic inputs only.

## Automated checks

| Python / Linux | Discovered | Passed | Skipped | Failed / errors |
|---|---:|---:|---:|---:|
| 3.11.17 | 47 | 47 | 0 | 0 / 0 |
| 3.12.14 | 47 | 47 | 0 | 0 / 0 |
| 3.14.4 | 47 | 47 | 0 | 0 / 0 |

The tests exercise actual source-order and timezone projection, missing and
future timestamps, stale work intent, unchanged Unicode text, night-shift
returns and explicit rest, quote/negation handling, valid and invalid memory
receipts, and the pass/corrected/blocked delivery paths.

An independent read-only review reproduced three gaps in a candidate:
negation in a later sentence suppressed a chronology conflict, a quoted
incorrect chronology was treated as a direct claim, and negated rest/return
wording cleared work intent. The release candidate corrects these specific
cases. The final 47-test suite includes those regressions and short-farewell
variants. This is bounded language coverage, not exhaustive Japanese parsing.

## Installed artifact and offline integration

The wheel and source distribution are built with setuptools. The wheel is
installed into a fresh virtual environment with `--no-index --no-deps`.
The installed package, console entry point and offline integration example
are exercised from outside the source checkout. The 47 tests also run against
the installed wheel. Runtime Python files are compared byte-for-byte with
the reviewed source. Asset hashes are supplied in `SHA256SUMS`.

The offline integration example has exactly three cases. A valid draft is
sent, a corrected draft is sent, and an unresolved draft is withheld. The
correction is a scripted callback. **No live model call or model-quality
benchmark is claimed for this package release.** A real application's model,
prompt, timeout behavior and UI/voice delivery paths require their own checks.

The repository includes a read-only-permission GitHub Actions workflow for
Python 3.11, 3.12 and 3.14. Its public run record identifies the exact tested
commit; it is separate from the local results in the table above. Official
checkout and setup-python actions are pinned to their resolved v7 commit IDs.

## Distribution boundary

Source, wheel, source distribution and release ZIP are assembled and inspected
against an explicit file allowlist. Checks exclude private identity markers,
application paths, credential patterns, conversation stores, generated caches,
and original application Git history. The license bytes match the existing
PolyForm Noncommercial 1.0.0 license used for the author's public packages.

The public copyright identifier and repository URL are intentional attribution.
All dialogue examples and dates are invented. No private logs or acceptance
transcripts are required to run the package.

## Practical limits

- Only the documented Japanese patterns are covered. Unsupported paraphrases
  may pass; natural statements may be falsely flagged.
- `pass` is not a general truth or intent certificate.
- The host controls receipt authenticity, model tools, memory writes, timeouts,
  and whether drafts are buffered before delivery.
- A successful correction remains subject to the same detector's coverage.
- Linux was exercised; this record does not claim Windows/macOS execution.
