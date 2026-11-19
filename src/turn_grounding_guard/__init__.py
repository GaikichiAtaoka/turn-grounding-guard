"""Temporal / Turn Grounding Guard: bounded checks plus a delivery gate."""
from .core import (
    CorrectionRequest, DialogueRecord, ExecutionReceipt, GuardResult, Issue,
    TurnEvidence, build_turn_evidence, correction_messages,
    detect_turn_contradictions, guard_reply, render_turn_evidence,
)

__version__ = "0.1.0"
__all__ = [
    "CorrectionRequest", "DialogueRecord", "ExecutionReceipt", "GuardResult",
    "Issue", "TurnEvidence", "build_turn_evidence", "correction_messages",
    "detect_turn_contradictions", "guard_reply", "render_turn_evidence",
]
