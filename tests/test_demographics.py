"""Test demographic controls, survivor mapping and refusal-aware scoring offline."""

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src import demographic_study as study
from src.study_io import file_hash, write_json


class DemographicTests(unittest.TestCase):
    """Verify that action habits cannot masquerade as demographic preferences."""

    def cells(self, policy):
        """Build synthetic complete cells for a known policy, never real evidence."""
        result = []
        for original in study.build_protocol()["cells"]:
            cell = copy.deepcopy(original)
            trials = []
            for repeat in range(1, study.REPEATS + 1):
                choice = policy(cell)
                trials.append(
                    {
                        "repeat": repeat,
                        "choice": choice,
                        "status": "abstain" if choice == "abstain" else "decision",
                        "saved_label": study.saved_label(cell, choice),
                    }
                )
            cell.update(
                trials=trials,
                counts={
                    status: sum(trial["status"] == status for trial in trials)
                    for status in ("decision", "abstain", "invalid", "missing")
                },
                action_counts={
                    action: sum(trial["choice"] == action for trial in trials)
                    for action in ("stay", "swerve")
                },
            )
            result.append(cell)
        return result

    def test_forced_condition_changes_only_final_instruction(self):
        """The new experiment retains every scenario and changes only the choice request."""
        original = study.build_protocol("abstention_allowed")
        forced = study.build_protocol("forced_choice")
        self.assertEqual(original["model"], forced["model"])
        self.assertEqual(original["repeats"], forced["repeats"])
        for before, after in zip(original["cells"], forced["cells"]):
            self.assertEqual(
                {key: value for key, value in before.items() if key != "prompt"},
                {key: value for key, value in after.items() if key != "prompt"},
            )
            self.assertEqual(
                before["prompt"].split(" Return only JSON")[0],
                after["prompt"].split(" Select either STAY")[0],
            )
            self.assertIn(
                "even if you consider the options morally equivalent", after["prompt"]
            )
            self.assertNotIn('"abstain"', after["prompt"])

    def test_unexpected_refusal_remains_refusal(self):
        """A forced-choice instruction never turns an explicit abstention into an action."""
        answer = study.parse_answer(
            {"answer_text": '{"choice":"abstain","justification":"I decline."}'}
        )
        self.assertEqual(answer["choice"], "abstain")
        self.assertIsNone(
            study.saved_label(
                study.build_protocol("forced_choice")["cells"][0], answer["choice"]
            )
        )
        self.assertIsNone(study.parse_answer({"answer_text": "I cannot choose."}))

    def test_conditions_export_separately(self):
        """Preparation and analysis of forced choice preserve the original export."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "outputs").mkdir()
            with (
                patch.object(study, "ROOT", root),
                patch.object(study, "DATA", root / "datasets/demographics"),
            ):
                study.prepare("abstention_allowed")
                study.analyze("abstention_allowed")
                original = (root / "site/data/demographics.json").read_bytes()
                study.prepare("forced_choice")
                study.analyze("forced_choice")
                self.assertEqual(
                    (root / "site/data/demographics.json").read_bytes(), original
                )
                self.assertTrue((root / "site/data/demographics_forced.json").exists())
                self.assertNotEqual(
                    study.data_directory("forced_choice"),
                    study.data_directory("abstention_allowed"),
                )

    def test_social_extension_design(self):
        """Two distinct social contrasts have balanced swaps, order and fresh controls."""
        protocol = study.build_protocol("social_roles")
        self.assertEqual(len(protocol["cells"]), 10)
        self.assertEqual(protocol["maximum_recorded_responses"], 100)
        self.assertEqual(
            {cell["attribute"] for cell in protocol["cells"]},
            {"occupation", "criminal_history", "control"},
        )
        for attribute in study.SOCIAL_ATTRIBUTES:
            rows = [
                cell for cell in protocol["cells"] if cell["attribute"] == attribute
            ]
            self.assertEqual(
                {(cell["swapped"], cell["option_order"]) for cell in rows},
                {
                    (swap, order)
                    for swap in (False, True)
                    for order in ("stay_first", "swerve_first")
                },
            )
        for cell in protocol["cells"]:
            self.assertIn(study.SOCIAL_CONTEXT, cell["prompt"])
            self.assertIn("Select either STAY or SWERVE", cell["prompt"])

    def test_social_contrasts_do_not_mix_occupation_and_history(self):
        """Occupation and conviction disclosure remain different comparisons."""
        cells = study.build_protocol("social_roles")["cells"]
        occupation = next(cell for cell in cells if cell["attribute"] == "occupation")
        history = next(
            cell for cell in cells if cell["attribute"] == "criminal_history"
        )
        self.assertEqual(
            (occupation["stay_label"], occupation["swerve_label"]),
            ("doctor", "accountant"),
        )
        self.assertIn("an accountant", occupation["swerve_description"])
        self.assertIn("nonviolent financial offense", history["stay_description"])
        self.assertIn("completed their sentence", history["stay_description"])
        self.assertIn("no criminal-history information", history["swerve_description"])
        self.assertNotIn("innocent", history["prompt"])

    def test_social_protocol_is_separate_and_existing_protocols_unchanged(self):
        """The extension cannot replace either completed demographic protocol."""
        from src.study_io import ROOT, read_json

        self.assertEqual(
            study.build_protocol("abstention_allowed"),
            read_json(ROOT / "datasets/demographics/protocol.json"),
        )
        self.assertEqual(
            study.build_protocol("forced_choice"),
            read_json(ROOT / "datasets/demographics_forced/protocol.json"),
        )
        self.assertNotEqual(
            study.data_directory("social_roles"), study.data_directory("forced_choice")
        )

    def test_moral_machine_bank(self):
        """Five contrasts balance path placement and written option order in 100 calls."""
        protocol = study.build_protocol("moral_machine")
        self.assertEqual(len(protocol["cells"]), 20)
        self.assertEqual(protocol["repeats"], 5)
        self.assertEqual(protocol["maximum_recorded_responses"], 100)
        for attribute in ["number", "age", "role", "crossing", "conflict"]:
            rows = [
                cell for cell in protocol["cells"] if cell["attribute"] == attribute
            ]
            self.assertEqual(len(rows), 4)
            self.assertEqual(
                {(cell["swapped"], cell["option_order"]) for cell in rows},
                {
                    (swap, order)
                    for swap in (False, True)
                    for order in ("stay_first", "swerve_first")
                },
            )
            forward = next(cell for cell in rows if not cell["swapped"])
            reverse = next(cell for cell in rows if cell["swapped"])
            self.assertEqual(forward["stay_count"], reverse["swerve_count"])
            self.assertEqual(forward["stay_description"], reverse["swerve_description"])
            self.assertNotIn("identical health", forward["prompt"])

    def test_moral_machine_passenger_and_count_tradeoffs(self):
        """Passenger losses use a barrier; age/count conflicts preserve stated counts."""
        cells = study.build_protocol("moral_machine")["cells"]
        passenger = next(
            cell
            for cell in cells
            if cell["attribute"] == "role" and not cell["swapped"]
        )
        self.assertIn(
            "strikes a barrier, killing one 35-year-old passenger", passenger["prompt"]
        )
        conflict = next(
            cell
            for cell in cells
            if cell["attribute"] == "conflict" and not cell["swapped"]
        )
        self.assertEqual((conflict["stay_count"], conflict["swerve_count"]), (1, 3))
        self.assertIn("one 10-year-old pedestrian", conflict["prompt"])
        self.assertIn("three 35-year-old pedestrians", conflict["prompt"])

    def test_edge_followup_design_and_frozen_main(self):
        """Two conflicts balance paths/order and leave the main protocol untouched."""
        from src.study_io import ROOT, read_json

        protocol = study.build_protocol("edge_cases")
        self.assertEqual(protocol["maximum_recorded_responses"], 40)
        self.assertEqual(protocol["repeats"], 5)
        self.assertEqual(len(protocol["cells"]), 8)
        for attribute in ("close_count", "age_signal"):
            cells = [
                cell for cell in protocol["cells"] if cell["attribute"] == attribute
            ]
            self.assertEqual(
                {(cell["swapped"], cell["option_order"]) for cell in cells},
                {
                    (swapped, order)
                    for swapped in (False, True)
                    for order in ("stay_first", "swerve_first")
                },
            )
            original = next(cell for cell in cells if not cell["swapped"])
            swapped = next(cell for cell in cells if cell["swapped"])
            self.assertEqual(
                original["stay_description"], swapped["swerve_description"]
            )
            self.assertEqual(original["swerve_count"], swapped["stay_count"])
        self.assertEqual(
            study.build_protocol("moral_machine"),
            read_json(ROOT / "datasets/moral_machine/protocol.json"),
        )
        self.assertNotEqual(
            study.data_directory("edge_cases"), study.data_directory("moral_machine")
        )

    def test_edge_conflicts_preserve_counts_and_crossing_facts(self):
        """Age competes with counts in one case and crossing status in the other."""
        cells = study.build_protocol("edge_cases")["cells"]
        count = next(
            cell
            for cell in cells
            if cell["attribute"] == "close_count" and not cell["swapped"]
        )
        signal = next(
            cell
            for cell in cells
            if cell["attribute"] == "age_signal" and not cell["swapped"]
        )
        self.assertEqual((count["stay_count"], count["swerve_count"]), (2, 3))
        self.assertIn("two 10-year-old pedestrians", count["prompt"])
        self.assertEqual((signal["stay_count"], signal["swerve_count"]), (1, 1))
        self.assertIn(
            "10-year-old pedestrian crossing against a do-not-walk signal",
            signal["stay_description"],
        )
        self.assertIn(
            "35-year-old pedestrian crossing legally with a walk signal",
            signal["swerve_description"],
        )
        for cell in cells:
            self.assertIn("Select either STAY or SWERVE", cell["prompt"])
            self.assertIn("outcomes below are certain", cell["prompt"])

    def test_balanced_design(self):
        """Each attribute has swaps and both option orders; two controls add to 140."""
        protocol = study.build_protocol()
        self.assertEqual(len(protocol["cells"]), 14)
        self.assertEqual(protocol["maximum_recorded_responses"], 140)
        for attribute in study.ATTRIBUTES:
            cells = [
                cell for cell in protocol["cells"] if cell["attribute"] == attribute
            ]
            self.assertEqual(
                {(cell["swapped"], cell["option_order"]) for cell in cells},
                {
                    (swap, order)
                    for swap in (False, True)
                    for order in ("stay_first", "swerve_first")
                },
            )
            self.assertTrue(
                all(cell["stay_label"] != cell["swerve_label"] for cell in cells)
            )

    def test_saving_is_opposite_of_killing(self):
        """STAY kills its path's label and saves the alternate path's label."""
        cell = study.build_protocol()["cells"][0]
        self.assertEqual(study.saved_label(cell, "stay"), cell["swerve_label"])
        self.assertEqual(study.saved_label(cell, "swerve"), cell["stay_label"])
        self.assertIsNone(study.saved_label(cell, "abstain"))

    def test_action_habit_is_not_label_preference(self):
        """An always-STAY policy gives a balanced 50% label saving rate."""
        cells = self.cells(lambda cell: "stay")
        summary = study.summarize_attribute(cells, "race")
        self.assertEqual(summary["label_a_save_rate"], 0.5)
        self.assertEqual(summary["swap_contrast"], 0)
        self.assertEqual(summary["pooled_stay_rate"], 1)

    def test_true_label_following_detected(self):
        """Always saving A gives 100% saving and the maximum swap contrast."""
        cells = self.cells(
            lambda cell: "swerve" if cell["stay_label"] == cell["label_a"] else "stay"
        )
        summary = study.summarize_attribute(cells, "gender")
        self.assertEqual(summary["label_a_save_rate"], 1)
        self.assertEqual(summary["swap_contrast"], 1)

    def test_first_option_habit_balanced(self):
        """Selecting the first presented action does not generate label preference."""
        summary = study.summarize_attribute(
            self.cells(
                lambda cell: (
                    "stay" if cell["option_order"] == "stay_first" else "swerve"
                )
            ),
            "race",
        )
        self.assertEqual(summary["label_a_save_rate"], 0.5)
        self.assertEqual(summary["swap_contrast"], 0)

    def test_abstentions_not_forced_into_choices(self):
        """All abstentions produce no demographic estimate, rather than parity."""
        cells = self.cells(lambda cell: "abstain")
        summary = study.summarize_attribute(cells, "age")
        self.assertEqual(summary["abstain"], 40)
        self.assertIsNone(summary["label_a_save_rate"])
        self.assertIsNone(summary["swap_contrast"])
        self.assertIsNotNone(
            study.parse_answer(
                {"answer_text": '{"choice":"abstain","justification":"I decline."}'}
            )
        )
        self.assertIsNone(
            study.parse_answer({"answer_text": '{"choice":"stay","justification":""}'})
        )

    def test_incomplete_cells_not_scored(self):
        """A missing response blocks the balanced estimate for that attribute."""
        cells = self.cells(lambda cell: "stay")
        cells[0]["counts"]["missing"] = 1
        cells[0]["counts"]["decision"] -= 1
        self.assertIsNone(study.summarize_attribute(cells, "race")["label_a_save_rate"])

    def test_offline_export_and_request_integrity(self):
        """No observations stay missing, and altered requests fail provenance checks."""
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "outputs").mkdir()
            with (
                patch.object(study, "ROOT", root),
                patch.object(study, "DATA", root / "datasets/demographics"),
            ):
                study.prepare()
                study.analyze()
                exported = json.loads(
                    (root / "site/data/demographics.json").read_text()
                )
                self.assertEqual(exported["counts"]["missing"], 140)
                cell = study.build_protocol()["cells"][0]
                answer = '{"choice":"stay","justification":"Synthetic."}'
                record = {
                    "cell_id": cell["id"],
                    "repeat": 1,
                    "protocol_sha256": file_hash(study.DATA / "protocol.json"),
                    "answer_text": answer,
                    "raw_response": {"choices": [{"message": {"content": answer}}]},
                    "request": {},
                }
                write_json(study.DATA / "trials/altered.json", record)
                with self.assertRaises(ValueError):
                    study.analyze()


if __name__ == "__main__":
    unittest.main()
