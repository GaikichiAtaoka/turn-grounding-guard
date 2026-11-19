from dataclasses import FrozenInstanceError
import json
import unittest

from turn_grounding_guard import (
    ExecutionReceipt, build_turn_evidence, correction_messages,
    detect_turn_contradictions, guard_reply, render_turn_evidence,
)


HISTORY = [
    {"role": "user", "time": "2026-01-15T07:10:00+09:00",
     "content": "おはよう、仕事してくるね。", "message_id": "u1"},
    {"role": "assistant", "time": "2026-01-15T07:10:04+09:00",
     "content": "行ってらっしゃい。", "message_id": "a1"},
]


def evidence(user="うん、またあとでね。", history=None, now="2026-01-15T07:45:00+09:00"):
    return build_turn_evidence(HISTORY if history is None else history,
        user_message=user, reference=now, turn_id="current")


def codes(reply, ev=None, **kwargs):
    return {i.code for i in detect_turn_contradictions(reply, ev or evidence(), **kwargs)}


class EvidenceTests(unittest.TestCase):
    def test_morning_and_original_ids(self):
        ev = evidence()
        self.assertTrue(ev.strong_morning_context)
        self.assertTrue(ev.assistant_replied_departure)
        self.assertEqual(ev.departure_message_id, "u1")
        self.assertEqual(ev.departure_reply_id, "a1")
        self.assertEqual(ev.timeline[0].text, HISTORY[0]["content"])

    def test_reference_timezone_is_local_not_fixed_japan(self):
        ev = evidence(history=[], user="おはよう、仕事してくるね。",
                      now="2026-01-15T07:45:00-05:00")
        self.assertTrue(ev.strong_morning_context)
        self.assertTrue(ev.reference_now.endswith("-05:00"))

    def test_naive_reference_rejected(self):
        with self.assertRaises(ValueError):
            evidence(now="2026-01-15T07:45:00")

    def test_naive_history_omitted_not_invented(self):
        ev = evidence(history=[{**HISTORY[0], "time": "2026-01-15T07:10:00"}])
        self.assertFalse(ev.strong_morning_context)
        self.assertEqual(ev.omitted_records, 1)

    def test_future_record_cannot_change_current_intent(self):
        rows = HISTORY + [{"role": "user", "time": "2026-01-16T07:00:00+09:00",
                           "content": "今から寝るね。", "message_id": "future"}]
        self.assertTrue(evidence(history=rows).strong_morning_context)

    def test_stale_departure_not_enforced(self):
        self.assertFalse(evidence(now="2026-01-15T09:00:01+09:00").strong_morning_context)

    def test_missing_record_does_not_forge_adjacency(self):
        rows = [HISTORY[0], {"role": "user", "content": "時刻がない発言"}, HISTORY[1]]
        self.assertFalse(evidence(history=rows).assistant_replied_departure)
        self.assertFalse(evidence(history=rows).strong_morning_context)

    def test_intervening_user_turn_does_not_forge_adjacency(self):
        rows = [HISTORY[0], {"role": "user", "time": "2026-01-15T07:10:01+09:00",
                            "content": "別のことも伝えるね。"}, HISTORY[1]]
        self.assertFalse(evidence(history=rows).assistant_replied_departure)

    def test_current_departure_has_no_invented_existing_reply(self):
        ev = evidence(user="おはよう、仕事してくるね。")
        self.assertTrue(ev.strong_morning_context)
        self.assertEqual(ev.departure_message_id, "current")
        self.assertFalse(ev.assistant_replied_departure)

    def test_out_of_order_times_rejected(self):
        with self.assertRaises(ValueError):
            evidence(history=list(reversed(HISTORY)))

    def test_no_silent_text_clipping(self):
        with self.assertRaises(ValueError):
            evidence(history=[{**HISTORY[0], "content": "あ" * 4001}])

    def test_evidence_is_frozen(self):
        ev = evidence()
        with self.assertRaises(FrozenInstanceError):
            ev.turn_id = "another"
        with self.assertRaises(FrozenInstanceError):
            ev.timeline[0].text = "changed"

    def test_evidence_render_preserves_unicode(self):
        ev = evidence(user="またあとでね🌱")
        self.assertIn("またあとでね🌱", render_turn_evidence(ev))
        self.assertIn('"message_id": "u1"', render_turn_evidence(ev))


class DetectionTests(unittest.TestCase):
    def test_sleep_sendoff(self):
        self.assertEqual(codes("気をつけてね。おやすみなさい。"), {"outdated_sleep_sendoff"})
        self.assertEqual(codes("おやすみ。"), {"outdated_sleep_sendoff"})

    def test_short_farewell_variants(self):
        for reply in ["おやすみね！", "おやすみなさい、太郎。"]:
            self.assertEqual(codes(reply), {"outdated_sleep_sendoff"})

    def test_explicit_rest_overrides_departure(self):
        self.assertEqual(codes("おやすみなさい。", evidence("予定が変わって、今から寝るね。")), set())

    def test_negated_rest_does_not_override_departure(self):
        ev = evidence("おはよう。今から寝るわけじゃない。仕事してくる。")
        self.assertFalse(ev.sleep_requested_in_current_message)
        self.assertTrue(ev.strong_morning_context)
        self.assertIn("outdated_sleep_sendoff", codes("おやすみなさい。", ev))

    def test_negated_return_does_not_override_departure(self):
        ev = evidence("まだ仕事終わったわけじゃないよ。")
        self.assertTrue(ev.strong_morning_context)

    def test_night_shift_return_is_valid(self):
        self.assertEqual(codes("おやすみなさい。", evidence("夜勤明けで帰ってきた。今から寝る。")), set())

    def test_morning_alone_is_not_work_evidence(self):
        self.assertEqual(codes("おやすみなさい。", evidence(history=[])), set())

    def test_quoted_sleep_and_past_statement_are_not_farewells(self):
        for reply in ["さっきの「おやすみなさい」は誤りでした。", "昨夜は、おやすみなさい。",
                      "例文は『おやすみなさい』です。", "夜勤明けなら、おやすみなさい。"]:
            with self.subTest(reply=reply):
                self.assertEqual(codes(reply), set())

    def test_long_quote_is_removed_before_tail_window(self):
        self.assertEqual(codes("引用:「" + "説明" * 1000 + "おやすみなさい。」"), set())

    def test_quoted_work_departure_is_not_current_intent(self):
        ev = evidence(history=[], user="例文は『おはよう、仕事してくるね』です。")
        self.assertFalse(ev.strong_morning_context)

    def test_explicit_negated_work_intent(self):
        ev = evidence(history=[], user="おはよう。仕事に行くつもりはない。")
        self.assertFalse(ev.strong_morning_context)

    def test_actual_adjacent_reply_disproves_claim(self):
        ev = evidence("直近の会話を確認して。")
        self.assertIn("invented_immediate_reply", codes("朝の挨拶の直後に『おやすみなさい』と返しました。", ev))

    def test_correct_separate_sequence_not_flagged(self):
        ev = evidence("直近の会話を確認して。")
        self.assertEqual(codes("朝の挨拶の直後に行ってらっしゃいと返し、その後おやすみなさいと言いました。", ev), set())

    def test_negated_false_chronology_not_flagged(self):
        ev = evidence("直近の会話を確認して。")
        self.assertEqual(codes("朝の挨拶の直後におやすみなさいと言ったのではありません。", ev), set())

    def test_apology_in_next_sentence_cannot_erase_chronology_conflict(self):
        ev = evidence("直近の会話を確認して。")
        for ending in ["申し訳ありません。", "これからはしません。"]:
            self.assertIn("invented_immediate_reply", codes(
                "朝の挨拶の直後におやすみなさいと返しました。" + ending, ev))

    def test_quoted_chronology_error_is_not_an_assertion(self):
        ev = evidence("直近の会話を確認して。")
        self.assertEqual(codes("『朝の挨拶の直後におやすみなさい』とある説明は誤りです。", ev), set())

    def test_no_history_request_no_chronology_gate(self):
        self.assertNotIn("invented_immediate_reply", codes("朝の挨拶の直後におやすみなさいと返しました。"))

    def test_unverified_persistent_memory_claim(self):
        self.assertEqual(codes("永続メモリを更新しました。"), {"unverified_memory_mutation"})

    def test_quoted_or_hypothetical_memory_claims(self):
        for reply in ["『永続メモリを更新しました』という例文です。", "仮に永続メモリを更新しましたというなら、証拠が必要です。",
                      "今の会話で理解を改めたよ。"]:
            self.assertEqual(codes(reply), set())

    def test_receipt_must_match_turn_action_and_success(self):
        claim = "永続メモリを保存しました。"
        invalid = [ExecutionReceipt("old", "memory.write", True, "r1"),
                   ExecutionReceipt("current", "memory.read", True, "r2"),
                   ExecutionReceipt("current", "memory.write", False, "r3")]
        for receipt in invalid:
            self.assertIn("unverified_memory_mutation", codes(claim, receipts=[receipt]))
        self.assertEqual(codes(claim, receipts=[ExecutionReceipt("current", "memory.write", True, "r4")]), set())

    def test_receipt_boolean_must_not_be_truthy_string(self):
        with self.assertRaises(ValueError):
            ExecutionReceipt("current", "memory.write", "false", "r1")

    def test_empty_candidate_is_not_deliverable(self):
        self.assertEqual(codes("   "), {"invalid_candidate"})


class DeliveryTests(unittest.TestCase):
    def test_pass_avoids_model_call(self):
        def forbidden(_):
            self.fail("No correction should be needed")
        result = guard_reply("またあとでね。", evidence(), regenerate=forbidden)
        self.assertEqual((result.status, result.reply, result.correction_attempts),
                         ("pass", "またあとでね。", 0))

    def test_detected_draft_with_no_correction_is_blocked(self):
        result = guard_reply("おやすみなさい。", evidence())
        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.reply)

    def test_corrected_text_is_rechecked_and_delivered(self):
        calls = []
        def correction(request):
            calls.append(request)
            self.assertEqual(request.issues[0].code, "outdated_sleep_sendoff")
            return "またあとでね。"
        result = guard_reply("おやすみなさい。", evidence(), regenerate=correction)
        self.assertEqual((result.status, result.reply), ("corrected", "またあとでね。"))
        self.assertEqual(len(calls), 1)

    def test_failed_correction_is_not_retried_or_delivered(self):
        calls = []
        def correction(request):
            calls.append(request)
            return "おやすみなさい。"
        result = guard_reply("おやすみなさい。", evidence(), regenerate=correction)
        self.assertEqual(result.status, "blocked")
        self.assertIsNone(result.reply)
        self.assertEqual(len(calls), 1)

    def test_new_error_in_replacement_is_blocked(self):
        result = guard_reply("おやすみなさい。", evidence(),
                             regenerate=lambda _: "永続メモリを更新しました。")
        self.assertIsNone(result.reply)
        self.assertEqual({i.code for i in result.remaining_issues}, {"unverified_memory_mutation"})

    def test_correction_exception_exposes_no_error_body(self):
        def failure(_):
            raise RuntimeError("private token or data should not be surfaced")
        result = guard_reply("おやすみなさい。", evidence(), regenerate=failure)
        self.assertEqual(result.error_type, "RuntimeError")
        self.assertNotIn("private token", repr(result))
        self.assertIsNone(result.reply)

    def test_nontext_correction_is_blocked(self):
        result = guard_reply("おやすみなさい。", evidence(), regenerate=lambda _: None)
        self.assertEqual(result.error_type, "TypeError")
        self.assertIsNone(result.reply)

    def test_receipts_cannot_be_swapped_during_correction(self):
        receipts = []
        def correction(_):
            receipts.append(ExecutionReceipt("current", "memory.write", True, "r1"))
            return "永続メモリを更新しました。"
        result = guard_reply("永続メモリを更新しました。", evidence(), receipts=receipts,
                             regenerate=correction)
        self.assertEqual(result.status, "blocked")

    def test_correction_prompt_keeps_data_and_instructions_separate(self):
        captured = []
        def correction(request):
            captured.extend(correction_messages(request))
            return "またあとでね。"
        guard_reply("おやすみなさい。", evidence(), regenerate=correction)
        self.assertEqual([m["role"] for m in captured], ["system", "user"])
        packet = json.loads(captured[1]["content"])
        self.assertEqual(packet["candidate_answer"], "おやすみなさい。")
        self.assertEqual(packet["evidence"]["turn_id"], "current")
        self.assertNotIn("約40分", captured[0]["content"] + captured[1]["content"])


if __name__ == "__main__":
    unittest.main()
