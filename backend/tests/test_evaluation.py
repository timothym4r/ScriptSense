from pathlib import Path

from app.evaluation.gold_loader import load_gold_annotations
from app.evaluation.metrics import EvaluationScorer
from app.evaluation.predictor import PredictionRunner


def test_evaluation_pipeline_runs_across_modes() -> None:
    data_dir = Path("evaluation_data/gold")
    annotations = load_gold_annotations(data_dir)
    predictor = PredictionRunner()
    scorer = EvaluationScorer()

    baseline_report = scorer.evaluate(
        annotations[0],
        predictor.predict(annotations[0], "baseline"),
        "baseline",
    )
    heuristic_report = scorer.evaluate(
        annotations[0],
        predictor.predict(annotations[0], "heuristic"),
        "heuristic",
    )

    speaker_baseline = next(item for item in baseline_report.summary if item.task == "speaker_attribution")
    speaker_heuristic = next(item for item in heuristic_report.summary if item.task == "speaker_attribution")

    assert speaker_baseline.total >= 1
    assert speaker_heuristic.exact_match >= speaker_baseline.exact_match


def test_llm_fallback_mode_improves_unresolved_cases() -> None:
    data_dir = Path("evaluation_data/gold")
    annotation = next(item for item in load_gold_annotations(data_dir) if item.script_id == "dr_maya_alias")
    predictor = PredictionRunner()
    scorer = EvaluationScorer()

    baseline = scorer.evaluate(annotation, predictor.predict(annotation, "baseline"), "baseline")
    heuristic = scorer.evaluate(annotation, predictor.predict(annotation, "heuristic"), "heuristic")
    fallback = scorer.evaluate(
        annotation,
        predictor.predict(annotation, "heuristic_llm_fallback"),
        "heuristic_llm_fallback",
    )

    baseline_action = next(item for item in baseline.summary if item.task == "action_attribution")
    heuristic_action = next(item for item in heuristic.summary if item.task == "action_attribution")
    fallback_action = next(item for item in fallback.summary if item.task == "action_attribution")

    assert heuristic_action.exact_match >= baseline_action.exact_match
    assert fallback_action.ambiguity_aware_rate >= heuristic_action.ambiguity_aware_rate
