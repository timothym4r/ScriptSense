from collections import defaultdict

from app.evaluation.types import (
    EvaluationCaseResult,
    GoldScriptAnnotation,
    GoldTarget,
    ModeEvaluationReport,
    OutcomeLabel,
    SystemMode,
    TaskMetrics,
    TaskName,
    TaskPrediction,
)


class EvaluationScorer:
    def evaluate(
        self,
        annotation: GoldScriptAnnotation,
        predictions: dict[str, list[TaskPrediction]],
        mode: SystemMode,
    ) -> ModeEvaluationReport:
        results: list[EvaluationCaseResult] = []

        for task_name in ("speaker_attribution", "mention_resolution", "action_attribution"):
            gold_targets = getattr(annotation, task_name)
            task_predictions = predictions[task_name]
            for gold in gold_targets:
                prediction = self._match_prediction(task_name, gold, task_predictions)
                results.append(
                    self._score_case(
                        annotation.script_id,
                        task_name,
                        gold,
                        prediction,
                    )
                )

        summary = self._summarize(results)
        errors = [result for result in results if result.outcome != "exact_match"]
        return ModeEvaluationReport(
            script_id=annotation.script_id,
            mode=mode,
            summary=summary,
            errors=errors,
        )

    def _match_prediction(
        self,
        task_name: TaskName,
        gold: GoldTarget,
        predictions: list[TaskPrediction],
    ) -> TaskPrediction:
        matches = [
            prediction
            for prediction in predictions
            if prediction.scene_number == gold.scene_number
            and prediction.element_index == gold.element_index
        ]
        if task_name == "mention_resolution":
            filtered = [
                prediction
                for prediction in matches
                if prediction.mention_text == gold.mention_text
            ]
            if len(filtered) >= gold.mention_occurrence:
                return filtered[gold.mention_occurrence - 1]
        if matches:
            return matches[0]
        return TaskPrediction(
            scene_number=gold.scene_number,
            element_index=gold.element_index,
            resolution_status="unresolved",
            mention_text=gold.mention_text,
        )

    def _score_case(
        self,
        script_id: str,
        task_name: TaskName,
        gold: GoldTarget,
        prediction: TaskPrediction,
    ) -> EvaluationCaseResult:
        outcome = self._determine_outcome(gold, prediction)
        return EvaluationCaseResult(
            script_id=script_id,
            task=task_name,
            scene_number=gold.scene_number,
            element_index=gold.element_index,
            mention_text=gold.mention_text,
            gold_status=gold.resolution_status,
            predicted_status=prediction.resolution_status,
            gold_characters=gold.acceptable_characters,
            predicted_character=prediction.predicted_character,
            predicted_candidates=prediction.candidate_characters,
            outcome=outcome,
            confidence=prediction.attribution_confidence,
        )

    def _determine_outcome(self, gold: GoldTarget, prediction: TaskPrediction) -> OutcomeLabel:
        gold_set = set(gold.acceptable_characters)
        predicted_set = set(prediction.candidate_characters)
        if prediction.predicted_character:
            predicted_set.add(prediction.predicted_character)

        if gold.resolution_status == "unresolved":
            if prediction.resolution_status == "unresolved":
                return "exact_match"
            return "incorrect"

        if prediction.resolution_status == "unresolved":
            return "unresolved"

        if prediction.predicted_character and prediction.predicted_character in gold_set:
            return "exact_match"

        if predicted_set.intersection(gold_set):
            return "ambiguous_match"

        return "incorrect"

    def _summarize(self, results: list[EvaluationCaseResult]) -> list[TaskMetrics]:
        grouped: dict[str, list[EvaluationCaseResult]] = defaultdict(list)
        for result in results:
            grouped[result.task].append(result)

        summary: list[TaskMetrics] = []
        for task_name, task_results in grouped.items():
            total = len(task_results)
            exact = sum(result.outcome == "exact_match" for result in task_results)
            ambiguous = sum(result.outcome == "ambiguous_match" for result in task_results)
            unresolved = sum(result.outcome == "unresolved" for result in task_results)
            incorrect = sum(result.outcome == "incorrect" for result in task_results)
            summary.append(
                TaskMetrics(
                    task=task_name,
                    total=total,
                    exact_match=exact,
                    ambiguous_match=ambiguous,
                    unresolved=unresolved,
                    incorrect=incorrect,
                    exact_match_rate=round(exact / total, 3) if total else 0.0,
                    ambiguity_aware_rate=round((exact + ambiguous) / total, 3) if total else 0.0,
                    unresolved_rate=round(unresolved / total, 3) if total else 0.0,
                )
            )
        return sorted(summary, key=lambda item: item.task)
