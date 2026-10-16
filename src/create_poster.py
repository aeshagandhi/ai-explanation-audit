"""Render the academic 24 × 24-inch HTML poster from saved experimental results.

The poster uses Duke Navy on white, embedded PDF fonts, a dilemma diagram,
and three reading columns pairing every experiment with its findings.
The default PDF is exported from the HTML; --format vector retains the older renderer.
No model API requests are made. Brand colors: https://brand.duke.edu/colors/
"""

import argparse
import os
import shutil
from pathlib import Path

os.environ.setdefault(
    "MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".cache/matplotlib")
)
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties
from matplotlib.patches import Circle, FancyArrowPatch, Rectangle

from src.study_io import ROOT, read_json

NAVY = "#012169"
INK = "#20262F"
MUTED = "#515A65"
LINE = "#CDD2D9"
PAPER = "#FFFFFF"
POINTS = 24 * 72


def wrapped_lines(axis, content, width, size, bold):
    """Wrap against rendered font widths instead of guessing by character count."""
    renderer = axis.figure.canvas.get_renderer()
    font = FontProperties(
        family="Times New Roman", size=size, weight="bold" if bold else "normal"
    )
    available = width * axis.get_window_extent(renderer).width
    lines = []
    for paragraph in content.split("\n"):
        line = ""
        for word in paragraph.split():
            candidate = f"{line} {word}".strip()
            measured = renderer.get_text_width_height_descent(candidate, font, False)[0]
            if line and measured > available:
                lines.append(line)
                line = word
            else:
                line = candidate
        lines.append(line)
    return lines


def text(axis, x, y, content, width, size=21, bold=False, color=INK, leading=1.25):
    """Place physically sized text and return the bottom of its reserved lines."""
    lines = wrapped_lines(axis, content, width, size, bold)
    for index, line in enumerate(lines):
        axis.text(
            x,
            y - index * size * leading / POINTS,
            line,
            fontsize=size,
            va="top",
            color=color,
            weight="bold" if bold else "normal",
            family="Times New Roman",
        )
    return y - len(lines) * size * leading / POINTS


def section_heading(axis, x, y, title, width):
    """Use one consistent academic heading and rule for each major section."""
    text(axis, x, y, title, width, size=25, bold=True, color=NAVY)
    axis.plot([x, x + width], [y - 0.022, y - 0.022], color=NAVY, lw=1.5)


def ratio(numerator, denominator):
    """Keep unavailable evidence visibly pending instead of showing a fake rate."""
    return f"{numerator}/{denominator}" if denominator else "Pending"


def person(axis, x, y):
    """Draw a neutral person symbol for the conceptual dilemma diagram."""
    axis.add_patch(Circle((x, y), 0.0045, facecolor=INK, edgecolor="none"))
    axis.plot([x, x], [y - 0.006, y - 0.020], color=INK, lw=1.8)
    axis.plot(
        [x - 0.006, x, x + 0.006], [y - 0.014, y - 0.009, y - 0.014], color=INK, lw=1.6
    )
    axis.plot(
        [x - 0.005, x, x + 0.005], [y - 0.028, y - 0.020, y - 0.028], color=INK, lw=1.6
    )


def dilemma_diagram(axis):
    """Show which people each action harms in one illustrative crash."""
    axis.add_patch(
        Rectangle((0.61, 0.775), 0.056, 0.029, facecolor=NAVY, edgecolor="none")
    )
    for x in (0.62, 0.646):
        axis.add_patch(
            Rectangle((x, 0.787), 0.014, 0.011, facecolor=PAPER, edgecolor="none")
        )
        axis.add_patch(Circle((x + 0.003, 0.773), 0.006, facecolor=INK, edgecolor="none"))
    for end in ((0.811, 0.802), (0.853, 0.748)):
        axis.add_patch(
            FancyArrowPatch((0.68, 0.789), end, arrowstyle="->", mutation_scale=20, lw=2, color=NAVY)
        )
    for x in (0.831, 0.853, 0.875, 0.897, 0.919):
        person(axis, x, 0.815)
    person(axis, 0.88, 0.765)
    text(axis, 0.712, 0.818, "STAY", 0.09, size=18, bold=True, color=NAVY)
    text(axis, 0.712, 0.760, "SWERVE", 0.10, size=18, bold=True, color=NAVY)
    text(axis, 0.835, 0.781, "Five die", 0.12, size=17)
    text(axis, 0.858, 0.731, "One dies", 0.10, size=17)


def experiment_rows(studies):
    """Explain the actual manipulation, response count and finding for each batch."""
    framing = studies["study"]["conditions"]
    main = framing["standard"]
    extra = framing["symmetric_restatement"]
    allowed = studies["demographics"]["counts"]
    forced = studies["demographics_forced"]["counts"]
    social = studies["demographics_social"]["counts"]
    moral = {
        row["attribute"]: row for row in studies["demographics_moral"]["attributes"]
    }
    edge = {
        row["attribute"]: row for row in studies["demographics_edges"]["attributes"]
    }
    challenge = studies["challenges"]
    return [
        (
            "1. Does wording matter?\n120 answers",
            "Eight situations compared death counts or certain versus risky outcomes. Each was written as numbers, survivors first, or deaths first, with five answers per version. For example, four deaths and six survivors became six survive and four die.",
            f"Changing wording produced {100*main['cross']:.2f}% disagreeing answer pairs, versus {100*main['within']:.2f}% for identical questions. These mild descriptions did not add variation beyond simply asking again.",
        ),
        (
            "2. Does restating help?\n120 answers",
            "The same eight situations, three descriptions and five repeats now required listing both actions' probabilities, deaths and survivors in the same format before choosing.",
            f"Identical questions and changed wording both gave {100*extra['within']:.2f}% disagreement. Variation was lower in this batch, but this small test does not establish a reliable benefit from restating.",
        ),
        (
            "3. Demographics: may decline\n140 answers",
            "With one person dying either way, separate tests compared Black with White, man with woman, and age 25 with 75, plus questions without labels. Fourteen question versions were asked ten times; declining was allowed.",
            f"The model declined {allowed['abstain']}/140 times, including most unlabeled questions. Only three choices remained, leaving too little evidence to estimate preferences between groups.",
        ),
        (
            "4. Demographics: must choose\n140 answers",
            "The same fourteen questions were repeated ten times, now requiring STAY or SWERVE. Both written orders were tested, and exchanging paths reversed which person each action saved.",
            f"The model chose STAY in {forced['decision']}/140 answers. Swapping paths saved each group half the time, but the action never changed, so equal saving totals do not establish fairness.",
        ),
        (
            "5. Occupation and history\n100 answers",
            "Separate comparisons tested doctor versus accountant, and a person who served a sentence for nonviolent financial crime versus someone with undisclosed history. Eight versions swapped paths and written order, with ten repeats and 20 unlabeled controls.",
            f"All {social['decision']}/100 answers chose STAY, including controls. These descriptions did not change the fixed action. Missing history does not mean innocence, and occupation was tested separately from conviction history.",
        ),
        (
            "6. Competing priorities\n100 answers",
            "Five Moral Machine-inspired comparisons tested number of lives, age, passenger/pedestrian role, crossing signals, and age versus number. Each had two outcome placements, two written orders and five repeats: 20 answers per comparison.",
            f"The model saved five adults over one {ratio(moral['number']['label_a_saved'], moral['number']['decision'])}; two children over two older adults {ratio(moral['age']['label_a_saved'], moral['age']['decision'])}; two legal crossers over two crossing against the signal 20/20; and three adults over one child 20/20. For one passenger versus one pedestrian, it always chose STAY, saving each 10/20.",
        ),
        (
            "7. Harder conflicts\n40 answers",
            "Two follow-ups asked about two children versus three adults, and a child crossing against the signal versus an adult crossing legally. Each used both outcome placements, both written orders and five repeats.",
            f"The three adults were saved {ratio(edge['close_count']['decision']-edge['close_count']['label_a_saved'], edge['close_count']['decision'])} times. In the age-versus-signal conflict, all 20 answers chose STAY, saving each person 10/20 as their paths exchanged.",
        ),
        (
            "8. Challenging a choice\n60 new answers",
            "Ten saved answers from experiment 6 each received three separate follow-ups: an ethical argument for the opposite choice, disagreement requesting reversal, or neutral reconsideration. Each follow-up was repeated twice.",
            f"All {challenge['counts']['kept']}/60 follow-ups kept the initial action, with 20/20 unchanged in each condition. This shows stability in these conversations, rather than evidence that the decisions were morally correct.",
        ),
    ]


def paired_table(axis, rows):
    """Use an unshaded, full-width table with concrete designs beside their results."""
    columns = ((0.04, 0.145), (0.205, 0.355), (0.59, 0.37))
    for (x, width), label in zip(
        columns, ("Question tested", "What the model was asked", "Result and interpretation")
    ):
        text(axis, x, 0.675, label, width, size=20, bold=True, color=NAVY)
    axis.plot([0.04, 0.96], [0.657, 0.657], color=NAVY, lw=1)
    y = 0.648
    size, leading = 19, 1.16
    for row in rows:
        count = max(
            len(wrapped_lines(axis, content, width, size, index == 0))
            for index, ((x, width), content) in enumerate(zip(columns, row))
        )
        height = count * size * leading / POINTS + 0.004
        for index, ((x, width), content) in enumerate(zip(columns, row)):
            text(
                axis, x, y, content, width, size=size, leading=leading,
                bold=index == 0, color=NAVY if index == 0 else INK,
            )
        y -= height
        axis.plot([0.04, 0.96], [y + 0.005, y + 0.005], color=LINE, lw=0.65)
    return y


def main():
    """Create a print-focused poster while preserving author and URL options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--author", default="Aesha Gandhi")
    parser.add_argument("--url", default="")
    parser.add_argument("--format", choices=("html", "vector"), default="html")
    parser.add_argument("--size", choices=("24x24", "24x36"), default="24x24", help="Poster width × height in inches; each size has separate output files.")
    parser.add_argument("--svg", action="store_true", help="Also export a matching outlined SVG from the HTML poster PDF (automatic for 24x36).")
    parser.add_argument("--html-only", action="store_true", help="Write HTML without launching a browser.")
    parser.add_argument("--channel", help="Browser channel for PDF export, such as chrome.")
    args = parser.parse_args()
    if args.html_only and args.format != "html":
        parser.error("--html-only requires --format html")
    if args.format == "vector" and (args.size != "24x24" or args.svg):
        parser.error("Use --format html for size selection and matching SVG export")
    studies = {
        name: read_json(ROOT / f"site/data/{name}.json")
        for name in (
            "study",
            "demographics_forced",
            "demographics",
            "demographics_social",
            "demographics_moral",
            "demographics_edges",
            "challenges",
            "explanation_analysis",
        )
    }
    if args.format == "html":
        from src.html_poster import export_poster
        export_poster(studies, experiment_rows(studies), args.author, args.url, args.html_only, args.channel, size=args.size, svg=args.svg or args.size == "24x36")
        return
    framing = studies["study"]
    recorded = (
        framing["counts"]["valid"]
        + framing["counts"]["invalid"]
        + sum(
            study["counts"][status]
            for name, study in studies.items()
            if name not in ("study", "explanation_analysis")
            for status in ("decision", "abstain", "invalid")
        )
    )
    plt.rcParams.update(
        {"font.family": "Times New Roman", "pdf.fonttype": 42, "svg.fonttype": "none"}
    )
    figure = plt.figure(figsize=(24, 24), facecolor=PAPER)
    axis = figure.add_axes([0, 0, 1, 1])
    axis.set(xlim=(0, 1), ylim=(0, 1))
    axis.axis("off")
    axis.add_patch(
        Rectangle((0.04, 0.978), 0.92, 0.006, facecolor=NAVY, edgecolor="none")
    )
    text(axis, 0.04, 0.959, args.author, 0.49, size=22, bold=True, color=NAVY)
    text(
        axis,
        0.04,
        0.929,
        "AI choices in self-driving car dilemmas",
        0.92,
        size=48,
        bold=True,
        color=NAVY,
    )
    text(
        axis,
        0.04,
        0.887,
        "Who should be saved? Ethical choices and AI explanations in fictional crashes",
        0.92,
        size=25,
    )

    section_heading(axis, 0.04, 0.847, "Problem and approach", 0.92)
    intro_bottom = text(
        axis, 0.04, 0.812,
        "The trolley problem asks whether redirecting harm is justified to save more lives. In this car version, failed brakes leave two harmful choices: STAY on the current path or SWERVE to another path. Python-written questions asked one text model, gpt-6.1-sol, to choose and explain why, producing 820 saved API answers. This audits written decisions, not an actual driving system.",
        0.52, size=21, leading=1.2,
    )
    if intro_bottom < 0.715:
        raise ValueError("Poster introduction overlaps the experiment heading.")
    dilemma_diagram(axis)

    section_heading(axis, 0.04, 0.710, "Experimental design and findings", 0.92)
    table_bottom = paired_table(axis, experiment_rows(studies))

    review = studies["explanation_analysis"]
    main_rule = next(row for row in review["checks"] if row["name"] == "Moral Machine-inspired dilemmas")
    discussion_top = table_bottom - 0.015
    section_heading(axis, 0.04, discussion_top, "Explanation evaluation", 0.52)
    review_bottom = text(
        axis, 0.04, discussion_top - 0.032,
        f"Across 62 selected explanations checked against the question facts, {review['facts_correct']['yes']}/62 were supported and one was unclear. For the five main comparisons, reasons from the first answers became rules such as saving more lives. These rules matched {ratio(main_rule['matches'], main_rule['scored'])} other choices, versus {ratio(main_rule['always_stay_matches'], main_rule['scored'])} when always guessing STAY. A rule favoring younger lives failed on three age answers. This is an after-the-fact consistency check, not a test of hidden reasoning.",
        0.52, size=18.5, leading=1.16,
    )
    section_heading(axis, 0.60, discussion_top, "Conclusion and limitations", 0.36)
    discussion_bottom = text(
        axis, 0.60, discussion_top - 0.032,
        "Choices sometimes favored more lives and sometimes stayed with STAY regardless of who survived. Explanations therefore need behavioral checks. Results concern one model and repeated fictional cases. Follow-ups differ in context and collection period. The explanation checks compare stated rules with choices after collection. Future work should test those rules on new cases.",
        0.36, size=18.5, leading=1.16,
    )
    if min(review_bottom, discussion_bottom) < 0.052:
        raise ValueError("Poster discussion overlaps the footer; shorten the prose before export.")

    axis.plot([0.04, 0.96], [0.047, 0.047], color=LINE, lw=1)
    text(
        axis,
        0.04,
        0.025,
        "References: Tversky & Kahneman (1981), Science, doi:10.1126/science.7455683; Awad et al. (2018), Nature, doi:10.1038/s41586-018-0637-6; Turpin et al. (2023), NeurIPS, arXiv:2305.04388.",
        0.92,
        size=12,
        color=MUTED,
    )
    if args.url:
        text(axis, 0.57, 0.957, f"Artifact: {args.url}", 0.39, size=14, color=NAVY)

    destination = ROOT / "outputs/poster"
    destination.mkdir(parents=True, exist_ok=True)
    for suffix in ("pdf", "svg", "png"):
        filename = (
            "class_fair_preview.png"
            if suffix == "png"
            else f"class_fair_24x24.{suffix}"
        )
        figure.savefig(destination / filename, dpi=150, facecolor=PAPER)
    plt.close(figure)
    shutil.copyfile(destination / "class_fair_24x24.pdf", ROOT / "site/data/poster.pdf")
    print(
        "Generated 24 × 24-inch academic poster: Duke Blue accents, vector PDF/SVG, and 150-dpi preview."
    )


if __name__ == "__main__":
    main()
