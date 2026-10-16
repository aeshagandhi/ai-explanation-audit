"""Rebuild the saved study results, explanation review and poster offline.

Run with the project's Python environment. This executes analysis commands,
not collectors, and never sends requests to the model API.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STEPS = [
    ("Wording results", "src.framing_study", ["analyze"]),
    (
        "Forced-choice results",
        "src.demographic_study",
        ["analyze", "--condition", "forced_choice"],
    ),
    (
        "Abstention-allowed comparison",
        "src.demographic_study",
        ["analyze", "--condition", "abstention_allowed"],
    ),
    (
        "Occupation/history extension",
        "src.demographic_study",
        ["analyze", "--condition", "social_roles"],
    ),
    (
        "Moral Machine-inspired dilemmas",
        "src.demographic_study",
        ["analyze", "--condition", "moral_machine"],
    ),
    (
        "Edge-case follow-up",
        "src.demographic_study",
        ["analyze", "--condition", "edge_cases"],
    ),
    ("Challenge follow-ups", "src.challenge_study", ["analyze"]),
    ("Explanation review", "src.analyze_explanations", []),
    ("Poster and site PDF", "src.create_poster", []),
]


def main():
    """Run each offline step, showing full output only when a step fails."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poster-browser", help="Browser channel for poster export, such as chrome.")
    args = parser.parse_args()
    print("Rebuilding from saved records. No model API calls will be made.", flush=True)
    for index, (label, module, arguments) in enumerate(STEPS, start=1):
        if module == "src.create_poster" and args.poster_browser:
            arguments = [*arguments, "--channel", args.poster_browser]
        result = subprocess.run(
            [sys.executable, "-m", module, *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        if result.stderr:
            print(result.stderr, file=sys.stderr, end="")
        if result.returncode:
            print(result.stdout, end="")
            raise SystemExit(result.returncode)
        print(f"{index}/{len(STEPS)}  {label}: complete", flush=True)
    review = json.loads((ROOT / "outputs/explanation_analysis.json").read_text())
    print(
        f"Saved results are in outputs/; {review['reviewed_responses']} reviewed explanations exported to the site."
    )
    print("View: python -m http.server 8766 --bind 127.0.0.1 --directory site")


if __name__ == "__main__":
    main()
