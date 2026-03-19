from pathlib import Path

from app.evaluation.parser_gold_loader import load_corrected_annotations
from app.evaluation.parser_metrics import ParserEvaluationScorer
from app.evaluation.parser_predictor import ParserPredictionRunner


def test_corrected_output_scores_perfectly() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "evaluation_data" / "parser_gold"
    annotations = load_corrected_annotations(data_dir)
    predictor = ParserPredictionRunner()
    scorer = ParserEvaluationScorer()

    for annotation in annotations:
        predicted = predictor.predict(annotation, "corrected_output")
        report = scorer.evaluate(annotation, predicted, "corrected_output")
        assert report.errors == []
        assert all(item.incorrect == 0 for item in report.summary)
        assert all(item.missing == 0 for item in report.summary)
        assert all(item.extra == 0 for item in report.summary)


def test_raw_parser_surfaces_known_messy_format_failures() -> None:
    data_dir = Path(__file__).resolve().parents[1] / "evaluation_data" / "parser_gold"
    annotations = {
        item.script_id: item for item in load_corrected_annotations(data_dir)
    }
    predictor = ParserPredictionRunner()
    scorer = ParserEvaluationScorer()

    predicted = predictor.predict(annotations["mixed_case_screenplay"], "raw_parser")
    report = scorer.evaluate(annotations["mixed_case_screenplay"], predicted, "raw_parser")

    assert any(error.task == "scene_detection" for error in report.errors)
    assert any(error.task == "speaker_attribution" for error in report.errors)
