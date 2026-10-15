"""Generate a 24-inch square poster from the saved framing-study evidence.

The PDF, SVG and preview use the same metrics as the UI. Missing observations
are shown as pending so the poster accurately reflects collection progress.
"""

import argparse
import os
import textwrap
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from src.study_io import ROOT, read_json

INK = "#20322d"
GREEN = "#285b4b"
PAPER = "#f6f3eb"


def text(axis, x, y, content, size=22, width=37, bold=False, color=INK):
    """Place wrapped text with a consistent physical line spacing."""
    lines = []
    for paragraph in content.split("\n"):
        lines.extend(textwrap.wrap(paragraph, width) or [""])
    for index, line in enumerate(lines):
        axis.text(
            x,
            y - index * size * 1.42 / 1728,
            line,
            fontsize=size,
            va="top",
            color=color,
            weight="bold" if bold else "normal",
            family="DejaVu Sans",
        )
    return y - len(lines) * size * 1.42 / 1728


def pct(value):
    """Format observed fractions without disguising absent data."""
    return "Pending" if value is None else f"{100*value:.1f}%"


def main():
    """Render one 24-by-24-inch page and editable companion files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author", default="Explainable AI course project")
    parser.add_argument("--url", default="")
    args = parser.parse_args()
    study = read_json(ROOT / "site/data/study.json")
    plt.rcParams["svg.fonttype"] = "none"
    figure = plt.figure(figsize=(24, 24), facecolor=PAPER)
    axis = figure.add_axes([0, 0, 1, 1])
    axis.set(xlim=(0, 1), ylim=(0, 1))
    axis.axis("off")
    text(
        axis, 0.045, 0.96, "SAME CRASH,\nDIFFERENT STORY", size=74, width=40, bold=True
    )
    text(
        axis,
        0.047,
        0.815,
        "Can wording change an AI's moral decisions?",
        size=34,
        width=75,
    )
    text(axis, 0.047, 0.755, args.author, size=20, width=100)
    axis.plot([0.045, 0.955], [0.725, 0.725], color=GREEN, lw=2)
    columns = [0.045, 0.36, 0.675]
    for x, heading in zip(
        columns, ["1 / SAME CONSEQUENCES", "2 / CONTROLLED TEST", "3 / WHAT WE FOUND"]
    ):
        text(axis, x, 0.70, heading, size=23, width=30, bold=True, color=GREEN)
    y = text(
        axis,
        columns[0],
        0.65,
        "A car cannot stop. Its options can be described through deaths or survivors. The facts stay the same. Does the decision?",
        width=36,
        size=22,
    )
    y = text(axis, columns[0], y - 0.03, "One uncertain example", width=36, bold=True)
    y = text(
        axis,
        columns[0],
        y - 0.02,
        "STAY: 1 death, certainly.\nSWERVE: 20% chance of 5 deaths; 80% chance of no deaths.\nTen people in total; all other people survive.",
        width=36,
        size=22,
    )
    text(
        axis,
        columns[0],
        y - 0.025,
        "Both actions have one expected death, but different risks. We do not prescribe a morally correct answer.",
        width=36,
        size=22,
    )
    y = text(
        axis,
        columns[1],
        0.65,
        "8 scenarios\n3 equivalent descriptions\n2 instruction conditions\n5 repeats per prompt\n= 240 planned responses",
        width=36,
        size=22,
        bold=True,
    )
    y = text(
        axis,
        columns[1],
        y - 0.025,
        "Four families: clear, close, equal expected harm, and lower expected harm with risk. Each is mirrored.",
        width=36,
        size=22,
    )
    y = text(
        axis,
        columns[1],
        y - 0.025,
        "Compare repeated identical prompts against equivalent descriptions.",
        width=36,
        size=22,
    )
    text(
        axis,
        columns[1],
        y - 0.025,
        "Intervention: restate both options symmetrically before choosing.",
        width=36,
        size=22,
    )
    standard = study["conditions"]["standard"]
    treated = study["conditions"]["symmetric_restatement"]
    y = text(
        axis,
        columns[2],
        0.65,
        f"{study['counts']['valid']}/240 valid responses\nModel: {study['protocol']['model']}",
        width=36,
        size=22,
    )
    for name, metric in [("Standard", standard), ("Symmetric restatement", treated)]:
        y = text(axis, columns[2], y - 0.025, name, width=36, size=22, bold=True)
        excess = (
            "pending"
            if metric["gap"] is None
            else f"{100 * metric['gap']:.1f} percentage points"
        )
        result = (
            f"Same-prompt disagreement: {pct(metric['within'])}\n"
            f"Cross-description disagreement: {pct(metric['cross'])}\n"
            f"Excess: {excess}\n{metric['complete_scenarios']}/8 complete scenarios"
        )
        y = text(axis, columns[2], y - 0.012, result, width=34, size=23)
    axis.add_patch(
        Rectangle((0.035, 0.115), 0.93, 0.205, facecolor="#e4e9df", edgecolor="none")
    )
    text(
        axis,
        0.055,
        0.30,
        "Variation appeared without excess framing disagreement.",
        size=30,
        width=85,
        bold=True,
    )
    text(
        axis,
        0.055,
        0.255,
        "We test behavioral consistency, not moral correctness or driving safety. One model alias, eight designed scenarios and five repeats limit generalization. Pairwise comparisons share responses; no population significance claim is made.",
        size=22,
        width=99,
    )
    text(
        axis,
        0.055,
        0.175,
        "Next: independent prompt-equivalence and explanation review; more scenarios; test whether explanations help people predict decisions.",
        size=23,
        width=102,
    )
    text(
        axis,
        0.045,
        0.085,
        "Explore: predict a choice, change the wording, reveal the recorded decisions and explanations.",
        size=23,
        width=105,
        bold=True,
    )
    text(
        axis,
        0.045,
        0.055,
        "Grounding: Tversky & Kahneman, Science (1981); Awad et al., Nature (2018); Turpin et al., NeurIPS (2023).",
        size=16,
        width=150,
    )
    if args.url:
        text(axis, 0.045, 0.031, args.url, size=16, width=140)
    destination = ROOT / "outputs/poster"
    destination.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "svg", "png"):
        filename = (
            "class_fair_preview.png"
            if suffix == "png"
            else f"class_fair_24x24.{suffix}"
        )
        figure.savefig(destination / filename, dpi=90, facecolor=PAPER)
    plt.close(figure)
    print("Generated a one-page 24 × 24-inch poster from current framing results.")


if __name__ == "__main__":
    main()
