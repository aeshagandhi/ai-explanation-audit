"""Test experimental controls and scoring using synthetic data, never API calls."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src import framing_study as study
from src.study_io import write_json, file_hash


class FramingTests(unittest.TestCase):
    """Guard equivalence, denominators and recorded-evidence integrity."""

    def test_balanced_design(self):
        """Every scenario has all frame/condition combinations and five repeats."""
        protocol = study.build_protocol()
        self.assertEqual(len(protocol["scenarios"]), 8)
        self.assertEqual(len(protocol["cells"]), 48)
        self.assertEqual(protocol["maximum_recorded_responses"], 240)
        self.assertEqual(len({cell["id"] for cell in protocol["cells"]}), 48)

    def test_distributions_and_mirroring(self):
        """Risk distributions are exhaustive and mirrored actions swap exactly."""
        cases = study.scenarios()
        for forward, mirrored in zip(cases[::2], cases[1::2]):
            self.assertEqual(forward["stay"], mirrored["swerve"])
            self.assertEqual(forward["swerve"], mirrored["stay"])
            for action in ("stay", "swerve"):
                self.assertAlmostEqual(
                    sum(row["probability"] for row in forward[action]), 1
                )
                for row in forward[action]:
                    self.assertEqual(row["deaths"] + row["survivors"], 10)

    def test_frames_preserve_all_facts(self):
        """Every renderer states both counts and the same outcome probabilities."""
        for case in study.scenarios():
            for frame in study.FRAMES:
                for action in ("stay", "swerve"):
                    text = study.describe(action, case[action], frame)
                    for row in case[action]:
                        self.assertIn(
                            f"{100 * row['probability']:g}% probability:", text
                        )
                        if frame == "neutral":
                            self.assertIn(
                                f"deaths = {row['deaths']}; survivors = {row['survivors']}",
                                text,
                            )
                        else:
                            self.assertIn(f"{row['deaths']} die", text)
                            self.assertIn(f"{row['survivors']} survive", text)

    def test_risk_contrasts(self):
        """Equal-expected and lower-expected cases implement their stated contrasts."""
        cases = {case["id"]: case for case in study.scenarios()}
        for name, expected in [
            ("equal_expected-forward", 1),
            ("lower_expected_risk-forward", 0.5),
        ]:
            value = sum(
                row["probability"] * row["deaths"] for row in cases[name]["swerve"]
            )
            self.assertAlmostEqual(value, expected)

    def test_mitigation_only_adds_instruction(self):
        """The intervention preserves the dilemma rather than changing its facts."""
        case = study.scenarios()[0]
        plain = study.prompt_for(case, "neutral", "standard")
        treated = study.prompt_for(case, "neutral", "symmetric_restatement")
        self.assertEqual(treated.replace(study.MITIGATION, ""), plain)

    def test_disagreement(self):
        """Within-prompt calculations use unordered distinct repeats."""
        self.assertEqual(study.disagreement(["stay", "stay", "swerve"]), 2 / 3)
        self.assertEqual(study.disagreement(["stay"] * 5, ["swerve"] * 5), 1)
        self.assertIsNone(study.disagreement(["stay"]))

    def test_stable_framing_shift(self):
        """A synthetic stable wording effect exceeds zero within-prompt noise."""
        groups = {
            "neutral": ["stay"] * 5,
            "survival_first": ["swerve"] * 5,
            "death_first": ["stay"] * 5,
        }
        measured = study.scenario_metric(groups)
        self.assertEqual(measured["within"], 0)
        self.assertAlmostEqual(measured["gap"], 2 / 3)

    def test_missing_or_invalid_not_scored(self):
        """Incomplete cells cannot quietly enter complete-scenario estimates."""
        self.assertIsNone(
            study.scenario_metric(
                {
                    frame: ["stay"] * (4 if frame == "neutral" else 5)
                    for frame in study.FRAMES
                }
            )
        )
        for text in [
            "{}",
            "not JSON",
            '{"choice":"swerve","justification":""}',
            "[1]",
            '{"choice":"maybe","justification":"stay"}',
        ]:
            self.assertIsNone(study.parse_answer({"answer_text": text}))

    def test_offline_export_and_tamper_detection(self):
        """Absent trials remain missing; altered request bodies fail verification."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            data = root / "datasets/framing"
            with patch.object(study, "ROOT", root), patch.object(study, "DATA", data):
                study.prepare()
                study.analyze()
                exported = json.loads((root / "site/data/study.json").read_text())
                self.assertEqual(
                    exported["counts"], {"valid": 0, "invalid": 0, "missing": 240}
                )
                self.assertIsNone(exported["conditions"]["standard"]["gap"])
                cell = study.build_protocol()["cells"][0]
                answer = '{"choice":"stay","justification":"Test only."}'
                record = {
                    "cell_id": cell["id"],
                    "repeat": 1,
                    "protocol_sha256": file_hash(data / "protocol.json"),
                    "answer_text": answer,
                    "raw_response": {"choices": [{"message": {"content": answer}}]},
                    "request": {
                        "model": study.MODEL,
                        "messages": [{"role": "user", "content": "changed prompt"}],
                        "response_format": {"type": "json_object"},
                    },
                }
                write_json(data / "trials/altered.json", record)
                with self.assertRaises(ValueError):
                    study.analyze()


if __name__ == "__main__":
    unittest.main()
