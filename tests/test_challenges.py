"""Check conversation branching, refusal-aware scoring and source integrity offline."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import challenge_study as study
from src import api_client
from src.study_io import file_hash, write_json


class ChallengeTests(unittest.TestCase):
    """Protect paired comparisons from changed context or invented action labels."""

    def test_design_and_fixed_branches(self):
        """Ten real source answers each branch into three conditions, twice."""
        protocol = study.build_protocol()
        self.assertEqual(len(protocol["anchors"]), 10)
        self.assertEqual(len(protocol["cells"]), 30)
        self.assertEqual(protocol["maximum_recorded_responses"], 60)
        for anchor in protocol["anchors"]:
            cells = [
                cell for cell in protocol["cells"] if cell["anchor_id"] == anchor["id"]
            ]
            self.assertEqual(
                {cell["condition"] for cell in cells}, set(study.CONDITIONS)
            )
            branches = [study.request_body(protocol, cell) for cell in cells]
            self.assertTrue(
                all(
                    branch["messages"][:2] == branches[0]["messages"][:2]
                    for branch in branches
                )
            )
            self.assertEqual(
                [row["role"] for row in branches[0]["messages"]],
                ["user", "assistant", "user"],
            )
            self.assertEqual(
                branches[0]["messages"][1]["content"], anchor["assistant_text"]
            )
            argument, disagreement, neutral = [
                branch["messages"][-1]["content"] for branch in branches
            ]
            self.assertIn(f"Please choose {anchor['target_choice'].upper()}.", argument)
            self.assertIn(
                f"Please choose {anchor['target_choice'].upper()}.", disagreement
            )
            self.assertNotIn("Please choose", neutral)
            self.assertTrue(
                all(
                    branch["messages"][-1]["content"].endswith(study.INSTRUCTION)
                    for branch in branches
                )
            )
            self.assertNotEqual(anchor["choice"], anchor["target_choice"])

    def test_refusal_missing_and_invalid_do_not_become_kept(self):
        """Only valid decisions enter changed/kept counts and survivor mapping."""
        anchor = {"choice": "stay", "saved_label": "A", "target_saved_label": "B"}
        raw = lambda choice: {
            "answer_text": json.dumps({"choice": choice, "justification": "Synthetic."})
        }
        rows = [
            study.score_trial(raw("stay"), anchor, 1),
            study.score_trial(raw("swerve"), anchor, 2),
            study.score_trial(raw("abstain"), anchor, 1),
            study.score_trial(None, anchor, 1),
            study.score_trial({"answer_text": "bad"}, anchor, 1),
        ]
        summary = study.summarize(rows)
        self.assertEqual(
            (summary["changed"], summary["kept"], summary["decision"]), (1, 1, 2)
        )
        self.assertEqual(
            (summary["abstain"], summary["missing"], summary["invalid"]), (1, 1, 1)
        )
        self.assertEqual(rows[1]["saved_label"], "B")
        self.assertTrue(all(row["changed"] is None for row in rows[2:]))

    def test_matched_denominators(self):
        """Missing decisions block the paired estimate instead of shrinking its bank."""
        cells = [
            {
                "anchor_id": str(index),
                "condition": condition,
                "counts": {
                    "decision": 2,
                    "change_rate": 1.0 if condition == "argument" else 0.0,
                },
            }
            for index in range(10)
            for condition in study.CONDITIONS
        ]
        result = study.matched_differences(cells)
        self.assertEqual(result["neutral"]["argument_minus_baseline"], 1.0)
        cells[0]["counts"]["decision"] = 1
        result = study.matched_differences(cells)
        self.assertEqual(result["neutral"]["matched_anchors"], 9)
        self.assertIsNone(result["neutral"]["argument_minus_baseline"])

    def test_existing_single_turn_requests_unchanged(self):
        """The shared API helper preserves old requests and forwards new branches."""
        with patch.object(api_client, "query_messages", return_value={}) as query:
            api_client.query("original", "model", "key")
            query.assert_called_once_with(
                [{"role": "user", "content": "original"}], "model", "key"
            )

    def test_changed_requests_and_duplicate_trials_rejected(self):
        """Offline analysis cannot silently accept modified prompts or double counts."""
        protocol = study.build_protocol()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data = root / "datasets/challenges"
            write_json(data / "protocol.json", protocol)
            answer = '{"choice":"stay","justification":"Synthetic."}'
            record = {
                "cell_id": protocol["cells"][0]["id"],
                "repeat": 1,
                "protocol_sha256": file_hash(data / "protocol.json"),
                "request": study.request_body(protocol, protocol["cells"][0]),
                "answer_text": answer,
                "raw_response": {"choices": [{"message": {"content": answer}}]},
            }
            write_json(data / "trials/one.json", record)
            with (
                patch.object(study, "ROOT", root),
                patch.object(study, "DATA", data),
                patch.object(study, "build_protocol", return_value=protocol),
            ):
                (root / "outputs").mkdir()
                study.analyze()
                changed = copy.deepcopy(record)
                changed["request"]["messages"][-1]["content"] = "changed"
                write_json(data / "trials/one.json", changed)
                with self.assertRaisesRegex(ValueError, "Changed challenge"):
                    study.analyze()
                write_json(data / "trials/one.json", record)
                write_json(data / "trials/two.json", record)
                with self.assertRaisesRegex(ValueError, "Duplicate"):
                    study.analyze()


if __name__ == "__main__":
    unittest.main()
