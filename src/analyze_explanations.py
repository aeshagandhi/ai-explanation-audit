"""Summarize completed explanation annotations and replay their explicit rules.

Annotations are a separate source artifact, not a keyword classifier. Verify
source hashes before exporting row-level judgments and retrospective prediction
checks. This script makes no API calls and never creates new review labels.
"""

import csv
import json
from collections import Counter

from src.study_io import ROOT, file_hash, read_json, write_json

PRINCIPLES = {
    "worst_case",
    "chance_no_deaths",
    "procedural_stay",
    "unclear",
    "min_deaths",
    "protect_children",
    "protect_legal",
    "legal_and_stay",
}


def predicted_action(case, principle):
    """Translate only an explicit coded principle; preserve ties as undetermined."""
    if principle == "procedural_stay":
        return "stay"
    if principle == "min_deaths":
        if case["stay_count"] == case["swerve_count"]:
            return None
        return "stay" if case["stay_count"] < case["swerve_count"] else "swerve"
    if principle in ("protect_children", "protect_legal", "legal_and_stay"):
        expected = (
            ("age", "conflict") if principle == "protect_children" else ("crossing",)
        )
        if case.get("attribute") not in expected:
            return None
        action = "swerve" if case["stay_label"] == case["label_a"] else "stay"
        return None if principle == "legal_and_stay" and action != "stay" else action
    if principle == "worst_case":
        values = {
            action: max(row["deaths"] for row in case[action])
            for action in ("stay", "swerve")
        }
        if values["stay"] == values["swerve"]:
            return None
        return min(values, key=values.get)
    if principle == "chance_no_deaths":
        values = {
            action: sum(
                row["probability"] for row in case[action] if row["deaths"] == 0
            )
            for action in ("stay", "swerve")
        }
        if values["stay"] == values["swerve"]:
            return None
        return max(values, key=values.get)
    if principle == "unclear":
        return None
    raise ValueError("Unknown coded principle.")


def validate_review(review):
    """Require unique, complete judgments that match unchanged raw responses."""
    seen = set()
    for row in review["records"]:
        relative = row["source_path"]
        path = ROOT / relative
        if relative in seen:
            raise ValueError("Duplicate reviewed response.")
        seen.add(relative)
        if file_hash(path) != row["source_sha256"]:
            raise ValueError("Reviewed source changed; inspect the annotation again.")
        record = read_json(path)
        answer = json.loads(record["answer_text"])
        if (
            record["answer_text"]
            != record["raw_response"]["choices"][0]["message"]["content"]
        ):
            raise ValueError("Stored response differs from raw provider output.")
        if (
            answer["choice"] != row["choice"]
            or answer["justification"] != row["justification"]
        ):
            raise ValueError("Annotation text or action differs from its source.")
        if row["principle"] not in PRINCIPLES:
            raise ValueError("Unknown annotation principle.")
        if any(
            row[key] not in {"yes", "no", "unclear"}
            for key in ("facts_correct", "supports_action")
        ):
            raise ValueError("Incomplete review judgment.")
        if not row.get("reviewer") or not row.get("notes"):
            raise ValueError("Reviewer attribution and explanatory notes are required.")


def verify_trial(record, protocol, digest):
    """Reject altered target prompts, protocol hashes and provider answer text."""
    cell = next(
        (cell for cell in protocol["cells"] if cell["id"] == record["cell_id"]), None
    )
    if cell is None or record["protocol_sha256"] != digest:
        raise ValueError("Replay target does not belong to this protocol.")
    expected = {
        "model": protocol["model"],
        "messages": [{"role": "user", "content": cell["prompt"]}],
        "response_format": {"type": "json_object"},
    }
    if (
        record["request"] != expected
        or record["answer_text"]
        != record["raw_response"]["choices"][0]["message"]["content"]
    ):
        raise ValueError(
            "Replay target differs from the frozen request or raw response."
        )
    repeat = record.get("repeat", record.get("repeat_id"))
    if type(repeat) is not int or not 1 <= repeat <= protocol["repeats"]:
        raise ValueError("Unplanned replay target repeat.")


def replay_check(name, anchors, targets, cases):
    """Compare retrospectively interpreted seed principles with recorded targets."""
    rows = []
    seen = set()
    for key, record in targets:
        identity = (record["cell_id"], record.get("repeat", record.get("repeat_id")))
        if identity in seen:
            raise ValueError("Duplicate replay target.")
        seen.add(identity)
        anchor = anchors[key]
        case = cases[record["cell_id"]] if record["cell_id"] in cases else cases[key]
        predicted = predicted_action(case, anchor["principle"])
        answer = json.loads(record["answer_text"])
        actual = answer.get("choice")
        scored = predicted is not None and actual in ("stay", "swerve")
        rows.append(
            {
                "anchor_path": anchor["source_path"],
                "target_id": (
                    record["cell_id"] if "cell_id" in record else record["case_id"]
                ),
                "repeat": record.get("repeat", record.get("repeat_id")),
                "principle": anchor["principle"],
                "predicted": predicted,
                "actual": actual,
                "scored": scored,
                "matches": predicted == actual if scored else None,
            }
        )
    scored = [row for row in rows if row["scored"]]
    return {
        "name": name,
        "targets": len(rows),
        "scored": len(scored),
        "matches": sum(row["matches"] for row in scored),
        "always_stay_matches": sum(row["actual"] == "stay" for row in scored),
        "rows": rows,
    }


def analyze():
    """Export review findings without presenting retrospective checks as validation."""
    review = read_json(ROOT / "datasets/explanation_review/annotations.json")
    validate_review(review)
    records = review["records"]
    framing_protocol = read_json(ROOT / "datasets/framing/protocol.json")
    demographic_protocol = read_json(
        ROOT / "datasets/demographics_forced/protocol.json"
    )
    framing_cases = {case["id"]: case for case in framing_protocol["scenarios"]}

    framing_anchors = {}
    demographic_anchors = {}
    moral_anchors = {}
    for row in records:
        raw = read_json(ROOT / row["source_path"])
        if (
            row["source_path"].startswith("datasets/framing/")
            and "__neutral__standard__r1" in row["source_path"]
        ):
            key = raw["cell_id"].split("__")[0]
            framing_anchors[key] = row
        if row["source_path"].startswith("datasets/demographics_forced/"):
            demographic_anchors[raw["cell_id"]] = row
        if (
            row["source_path"].startswith("datasets/moral_machine/")
            and "__original__stay_first__r1" in row["source_path"]
        ):
            moral_anchors[raw["cell_id"].split("__")[0]] = row
    framing_targets = []
    for path in sorted((ROOT / "datasets/framing/trials").glob("*.json")):
        record = read_json(path)
        verify_trial(
            record, framing_protocol, file_hash(ROOT / "datasets/framing/protocol.json")
        )
        key = record["cell_id"].split("__")[0]
        if (
            key in framing_anchors
            and "__standard" in record["cell_id"]
            and str(path.relative_to(ROOT)) != framing_anchors[key]["source_path"]
        ):
            framing_targets.append((key, record))
    demographic_targets = []
    for path in sorted((ROOT / "datasets/demographics_forced/trials").glob("*.json")):
        record = read_json(path)
        verify_trial(
            record,
            demographic_protocol,
            file_hash(ROOT / "datasets/demographics_forced/protocol.json"),
        )
        key = record["cell_id"]
        if key in demographic_anchors and record["repeat"] != 1:
            demographic_targets.append((key, record))
    moral_protocol = read_json(ROOT / "datasets/moral_machine/protocol.json")
    moral_targets = []
    for path in sorted((ROOT / "datasets/moral_machine/trials").glob("*.json")):
        record = read_json(path)
        verify_trial(
            record,
            moral_protocol,
            file_hash(ROOT / "datasets/moral_machine/protocol.json"),
        )
        key = record["cell_id"].split("__")[0]
        if str(path.relative_to(ROOT)) != moral_anchors[key]["source_path"]:
            moral_targets.append((key, record))
    checks = [
        replay_check(
            "Equal-expected-harm scenarios",
            framing_anchors,
            framing_targets,
            framing_cases,
        ),
        replay_check(
            "Forced-choice demographic cells",
            demographic_anchors,
            demographic_targets,
            {key: {} for key in demographic_anchors},
        ),
    ]
    checks.append(
        replay_check(
            "Moral Machine-inspired dilemmas",
            moral_anchors,
            moral_targets,
            {cell["id"]: cell for cell in moral_protocol["cells"]},
        )
    )
    summary = {
        "reviewed_responses": len(records),
        "main_reviewed_responses": sum(
            row["source_path"].startswith("datasets/moral_machine/") for row in records
        ),
        "supporting_reviewed_responses": sum(
            not row["source_path"].startswith("datasets/moral_machine/")
            for row in records
        ),
        "principle_counts": dict(Counter(row["principle"] for row in records)),
        "facts_correct": dict(Counter(row["facts_correct"] for row in records)),
        "supports_action": dict(Counter(row["supports_action"] for row in records)),
        "review_status": review["review_status"],
        "annotation_source": review["annotation_source"],
        "human_review_status": review["human_review_status"],
        "scope": "Retrospective non-blinded subset; not representative of the full study; excludes the occupation/history extension. No independent human validation, prospective prediction test or internal-faithfulness claim.",
        "selection": review["selection"],
        "rubric": review["rubric"],
        "codebook": review["codebook"],
        "annotations_sha256": file_hash(
            ROOT / "datasets/explanation_review/annotations.json"
        ),
        "checks": checks,
        "annotations": records,
    }
    write_json(ROOT / "outputs/explanation_analysis.json", summary)
    write_json(ROOT / "site/data/explanation_analysis.json", summary)
    with (ROOT / "outputs/explanation_review.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (ROOT / "site/data/explanation_review.csv").write_bytes(
        (ROOT / "outputs/explanation_review.csv").read_bytes()
    )
    print(
        f"Reviewed {len(records)} explanations. Replay checks: "
        + ", ".join(f"{check['matches']}/{check['scored']}" for check in checks)
    )


if __name__ == "__main__":
    analyze()
