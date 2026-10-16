"""Check explanation replay scoring and source integrity without model calls."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import analyze_explanations as analysis
from src.study_io import file_hash, write_json


class ExplanationTests(unittest.TestCase):
    """Ensure explicit principles, unknowns and target denominators stay distinct."""

    def case(self):
        """Return a synthetic one-certain-versus-five-risk scenario."""
        return {
            "stay": [{"probability": 1, "deaths": 1}],
            "swerve": [
                {"probability": 0.2, "deaths": 5},
                {"probability": 0.8, "deaths": 0},
            ],
        }

    def test_principles_choose_distinct_actions(self):
        """Worst-case avoidance and chance-of-zero choose opposite risk options."""
        self.assertEqual(analysis.predicted_action(self.case(), "worst_case"), "stay")
        self.assertEqual(
            analysis.predicted_action(self.case(), "chance_no_deaths"), "swerve"
        )
        self.assertEqual(analysis.predicted_action({}, "procedural_stay"), "stay")

    def test_ties_and_unclear_not_forced(self):
        """A principle that does not distinguish options yields no prediction."""
        case = self.case()
        case["swerve"] = copy.deepcopy(case["stay"])
        self.assertIsNone(analysis.predicted_action(case, "worst_case"))
        self.assertIsNone(analysis.predicted_action(case, "chance_no_deaths"))
        self.assertIsNone(analysis.predicted_action(case, "unclear"))
        with self.assertRaises(ValueError):
            analysis.predicted_action(case, "invented")

    def test_baseline_and_undetermined_denominators(self):
        """An unresolved anchor is excluded and the baseline uses the same targets."""
        anchors = {
            "a": {"principle": "worst_case", "source_path": "a"},
            "b": {"principle": "unclear", "source_path": "b"},
        }
        targets = [
            ("a", {"cell_id": "a", "repeat": 2, "answer_text": '{"choice":"stay"}'}),
            ("b", {"cell_id": "b", "repeat": 2, "answer_text": '{"choice":"swerve"}'}),
        ]
        check = analysis.replay_check(
            "test", anchors, targets, {"a": self.case(), "b": self.case()}
        )
        self.assertEqual(
            (
                check["targets"],
                check["scored"],
                check["matches"],
                check["always_stay_matches"],
            ),
            (2, 1, 1, 1),
        )
        with self.assertRaises(ValueError):
            analysis.replay_check(
                "test", anchors, [targets[0], targets[0]], {"a": self.case()}
            )

    def test_count_priority_and_swapped_outcomes(self):
        """A count rule follows the smaller death toll and preserves ties."""
        case = {"stay_count": 5, "swerve_count": 1}
        self.assertEqual(analysis.predicted_action(case, "min_deaths"), "swerve")
        case.update(stay_count=1, swerve_count=5)
        self.assertEqual(analysis.predicted_action(case, "min_deaths"), "stay")
        case.update(swerve_count=1)
        self.assertIsNone(analysis.predicted_action(case, "min_deaths"))

    def test_group_rules_and_mixed_principles(self):
        """Group rules follow placements; mixed reasons cannot invent a priority."""
        case = {"attribute": "crossing", "label_a": "legal", "stay_label": "legal"}
        self.assertEqual(analysis.predicted_action(case, "protect_legal"), "swerve")
        self.assertIsNone(analysis.predicted_action(case, "legal_and_stay"))
        case["stay_label"] = "against"
        self.assertEqual(analysis.predicted_action(case, "legal_and_stay"), "stay")
        self.assertIsNone(analysis.predicted_action(case, "protect_children"))
        case.update(attribute="age", label_a="children", stay_label="children")
        self.assertEqual(analysis.predicted_action(case, "protect_children"), "swerve")

    def test_review_rejects_changed_source(self):
        """A previously reviewed answer cannot be silently altered afterward."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            raw = {
                "answer_text": '{"choice":"stay","justification":"Tie."}',
                "raw_response": {
                    "choices": [
                        {
                            "message": {
                                "content": '{"choice":"stay","justification":"Tie."}'
                            }
                        }
                    ]
                },
            }
            write_json(root / "trial.json", raw)
            row = {
                "source_path": "trial.json",
                "source_sha256": file_hash(root / "trial.json"),
                "choice": "stay",
                "justification": "Tie.",
                "facts_correct": "yes",
                "supports_action": "yes",
                "principle": "procedural_stay",
                "reviewer": "Test fixture",
                "notes": "Synthetic.",
            }
            with patch.object(analysis, "ROOT", root):
                analysis.validate_review({"records": [row]})
                raw["answer_text"] = "changed"
                write_json(root / "trial.json", raw)
                with self.assertRaises(ValueError):
                    analysis.validate_review({"records": [row]})

    def test_target_request_integrity(self):
        """Prediction comparisons reject altered target prompt bodies."""
        protocol = {
            "model": "test",
            "repeats": 5,
            "cells": [{"id": "a", "prompt": "fixed"}],
        }
        answer = '{"choice":"stay"}'
        record = {
            "cell_id": "a",
            "repeat": 2,
            "protocol_sha256": "digest",
            "answer_text": answer,
            "raw_response": {"choices": [{"message": {"content": answer}}]},
            "request": {
                "model": "test",
                "messages": [{"role": "user", "content": "fixed"}],
                "response_format": {"type": "json_object"},
            },
        }
        analysis.verify_trial(record, protocol, "digest")
        record["request"]["messages"][0]["content"] = "changed"
        with self.assertRaises(ValueError):
            analysis.verify_trial(record, protocol, "digest")


if __name__ == "__main__":
    unittest.main()
