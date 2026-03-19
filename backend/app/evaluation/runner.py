import argparse
import json
from pathlib import Path

from app.evaluation.gold_loader import load_gold_annotations
from app.evaluation.metrics import EvaluationScorer
from app.evaluation.predictor import PredictionRunner
from app.evaluation.types import ModeEvaluationReport, SystemMode


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ScriptSense evaluation.")
    parser.add_argument(
        "--data-dir",
        default="evaluation_data/gold",
        help="Directory containing gold annotation JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation_data/output",
        help="Directory where evaluation reports will be written.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["baseline", "heuristic", "heuristic_llm_fallback"],
        choices=["baseline", "heuristic", "heuristic_llm_fallback"],
        help="System modes to evaluate.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    annotations = load_gold_annotations(data_dir)
    predictor = PredictionRunner()
    scorer = EvaluationScorer()

    all_reports: dict[str, list[ModeEvaluationReport]] = {}

    for mode in args.modes:
        mode_reports: list[ModeEvaluationReport] = []
        for annotation in annotations:
            predictions = predictor.predict(annotation, mode)
            report = scorer.evaluate(annotation, predictions, mode)
            mode_reports.append(report)
        all_reports[mode] = mode_reports
        write_mode_outputs(mode, mode_reports, output_dir)
        print_mode_summary(mode, mode_reports)

    combined_output = {
        mode: [report.model_dump() for report in reports] for mode, reports in all_reports.items()
    }
    (output_dir / "combined_report.json").write_text(json.dumps(combined_output, indent=2))


def write_mode_outputs(mode: SystemMode, reports: list[ModeEvaluationReport], output_dir: Path) -> None:
    mode_dir = output_dir / mode
    mode_dir.mkdir(parents=True, exist_ok=True)
    for report in reports:
        payload = report.model_dump()
        (mode_dir / f"{report.script_id}.json").write_text(json.dumps(payload, indent=2))


def print_mode_summary(mode: SystemMode, reports: list[ModeEvaluationReport]) -> None:
    print(f"\n=== {mode} ===")
    aggregate: dict[str, dict[str, float]] = {}
    for report in reports:
        for item in report.summary:
            bucket = aggregate.setdefault(
                item.task,
                {
                    "total": 0,
                    "exact_match": 0,
                    "ambiguous_match": 0,
                    "unresolved": 0,
                    "incorrect": 0,
                },
            )
            bucket["total"] += item.total
            bucket["exact_match"] += item.exact_match
            bucket["ambiguous_match"] += item.ambiguous_match
            bucket["unresolved"] += item.unresolved
            bucket["incorrect"] += item.incorrect

    for task_name, values in sorted(aggregate.items()):
        total = int(values["total"])
        exact = int(values["exact_match"])
        ambiguous = int(values["ambiguous_match"])
        unresolved = int(values["unresolved"])
        incorrect = int(values["incorrect"])
        ambiguity_aware_rate = round((exact + ambiguous) / total, 3) if total else 0.0
        print(
            f"{task_name}: total={total} exact={exact} ambiguous={ambiguous} "
            f"unresolved={unresolved} incorrect={incorrect} ambiguity_aware_rate={ambiguity_aware_rate}"
        )


if __name__ == "__main__":
    main()
