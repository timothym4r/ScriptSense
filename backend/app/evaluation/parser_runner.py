import argparse
import json
from pathlib import Path

from app.evaluation.parser_gold_loader import load_corrected_annotations
from app.evaluation.parser_metrics import ParserEvaluationScorer
from app.evaluation.parser_predictor import ParserPredictionRunner
from app.evaluation.parser_types import ParserEvalMode, ParserModeEvaluationReport


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run ScriptSense parser evaluation.")
    parser.add_argument(
        "--data-dir",
        default="evaluation_data/parser_gold",
        help="Directory containing corrected-data evaluation JSON files.",
    )
    parser.add_argument(
        "--output-dir",
        default="evaluation_data/parser_output",
        help="Directory where parser evaluation reports will be written.",
    )
    parser.add_argument(
        "--modes",
        nargs="+",
        default=["raw_parser", "corrected_output"],
        choices=["raw_parser", "corrected_output"],
        help="Parser modes to evaluate.",
    )
    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    annotations = load_corrected_annotations(data_dir)
    predictor = ParserPredictionRunner()
    scorer = ParserEvaluationScorer()

    all_reports: dict[str, list[ParserModeEvaluationReport]] = {}
    for mode in args.modes:
        mode_reports: list[ParserModeEvaluationReport] = []
        for annotation in annotations:
            predicted = predictor.predict(annotation, mode)
            report = scorer.evaluate(annotation, predicted, mode)
            mode_reports.append(report)
        all_reports[mode] = mode_reports
        write_mode_outputs(mode, mode_reports, output_dir)
        print_mode_summary(mode, mode_reports)

    combined_output = {
        mode: [report.model_dump() for report in reports] for mode, reports in all_reports.items()
    }
    (output_dir / "combined_report.json").write_text(json.dumps(combined_output, indent=2))


def write_mode_outputs(mode: ParserEvalMode, reports: list[ParserModeEvaluationReport], output_dir: Path) -> None:
    mode_dir = output_dir / mode
    mode_dir.mkdir(parents=True, exist_ok=True)
    for report in reports:
        payload = report.model_dump()
        (mode_dir / f"{report.script_id}.json").write_text(json.dumps(payload, indent=2))


def print_mode_summary(mode: ParserEvalMode, reports: list[ParserModeEvaluationReport]) -> None:
    print(f"\n=== {mode} ===")
    aggregate: dict[str, dict[str, float]] = {}
    for report in reports:
        for item in report.summary:
            bucket = aggregate.setdefault(
                item.task,
                {
                    "gold_total": 0,
                    "predicted_total": 0,
                    "exact_match": 0,
                    "missing": 0,
                    "extra": 0,
                    "incorrect": 0,
                },
            )
            bucket["gold_total"] += item.gold_total
            bucket["predicted_total"] += item.predicted_total
            bucket["exact_match"] += item.exact_match
            bucket["missing"] += item.missing
            bucket["extra"] += item.extra
            bucket["incorrect"] += item.incorrect

    for task_name, values in sorted(aggregate.items()):
        gold_total = int(values["gold_total"])
        predicted_total = int(values["predicted_total"])
        exact = int(values["exact_match"])
        missing = int(values["missing"])
        extra = int(values["extra"])
        incorrect = int(values["incorrect"])
        precision = round(exact / predicted_total, 3) if predicted_total else 0.0
        recall = round(exact / gold_total, 3) if gold_total else 0.0
        print(
            f"{task_name}: gold={gold_total} predicted={predicted_total} "
            f"exact={exact} missing={missing} extra={extra} incorrect={incorrect} "
            f"precision={precision} recall={recall}"
        )


if __name__ == "__main__":
    main()
