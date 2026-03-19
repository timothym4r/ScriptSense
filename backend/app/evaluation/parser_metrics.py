from typing import Dict, Iterable, Optional, Tuple

from app.evaluation.parser_types import (
    CorrectedBlockAnnotation,
    CorrectedSceneAnnotation,
    CorrectedScriptAnnotation,
    ParserCaseResult,
    ParserModeEvaluationReport,
    ParserOutcomeLabel,
    ParserTaskMetrics,
)
from app.schemas.parse import ParsedElement, ParsedScene, ParsedScriptResponse


class ParserEvaluationScorer:
    def evaluate(
        self,
        annotation: CorrectedScriptAnnotation,
        predicted: ParsedScriptResponse,
        mode: str,
    ) -> ParserModeEvaluationReport:
        results: list[ParserCaseResult] = []
        results.extend(self._evaluate_scene_detection(annotation, predicted))
        results.extend(self._evaluate_block_types(annotation, predicted))
        results.extend(self._evaluate_speakers(annotation, predicted))
        summary = self._summarize(results, annotation, predicted)
        errors = [result for result in results if result.outcome != "exact_match"]
        return ParserModeEvaluationReport(
            script_id=annotation.script_id,
            mode=mode,
            summary=summary,
            errors=errors,
        )

    def _evaluate_scene_detection(
        self,
        annotation: CorrectedScriptAnnotation,
        predicted: ParsedScriptResponse,
    ) -> list[ParserCaseResult]:
        results: list[ParserCaseResult] = []
        predicted_by_number = {scene.scene_number: scene for scene in predicted.scenes}
        gold_numbers = set()

        for gold_scene in annotation.corrected_scenes:
            gold_numbers.add(gold_scene.scene_number)
            predicted_scene = predicted_by_number.get(gold_scene.scene_number)
            if predicted_scene is None:
                results.append(
                    ParserCaseResult(
                        script_id=annotation.script_id,
                        task="scene_detection",
                        outcome="missing",
                        scene_number=gold_scene.scene_number,
                        gold_value=self._scene_signature(gold_scene),
                        predicted_value=None,
                        detail="Gold scene was not detected by the parser.",
                    )
                )
                continue

            heading_matches = self._normalize(gold_scene.heading) == self._normalize(predicted_scene.heading)
            boundaries_match = (
                gold_scene.start_line == predicted_scene.start_line
                and gold_scene.end_line == predicted_scene.end_line
            )
            outcome = "exact_match" if heading_matches and boundaries_match else "incorrect"
            results.append(
                ParserCaseResult(
                    script_id=annotation.script_id,
                    task="scene_detection",
                    outcome=outcome,
                    scene_number=gold_scene.scene_number,
                    gold_value=self._scene_signature(gold_scene),
                    predicted_value=self._scene_signature(predicted_scene),
                    detail=(
                        "Scene heading and line boundaries match."
                        if outcome == "exact_match"
                        else "Scene heading or boundaries differ from corrected output."
                    ),
                )
            )

        for predicted_scene in predicted.scenes:
            if predicted_scene.scene_number in gold_numbers:
                continue
            results.append(
                ParserCaseResult(
                    script_id=annotation.script_id,
                    task="scene_detection",
                    outcome="extra",
                    scene_number=predicted_scene.scene_number,
                    gold_value=None,
                    predicted_value=self._scene_signature(predicted_scene),
                    detail="Parser produced an extra scene not present in corrected output.",
                )
            )
        return results

    def _evaluate_block_types(
        self,
        annotation: CorrectedScriptAnnotation,
        predicted: ParsedScriptResponse,
    ) -> list[ParserCaseResult]:
        results: list[ParserCaseResult] = []
        predicted_blocks = self._predicted_blocks_by_key(predicted, include_scene_heading=False)
        gold_blocks = self._gold_blocks(annotation, include_scene_heading=False)
        seen_keys = set()

        for scene, gold_block in gold_blocks:
            key = self._block_key(scene.scene_number, gold_block.start_line, gold_block.end_line)
            seen_keys.add(key)
            predicted_block = predicted_blocks.get(key)
            if predicted_block is None:
                results.append(
                    ParserCaseResult(
                        script_id=annotation.script_id,
                        task="block_type_classification",
                        outcome="missing",
                        scene_number=scene.scene_number,
                        block_key=key,
                        text_excerpt=self._excerpt(gold_block.text),
                        gold_value=gold_block.element_type,
                        predicted_value=None,
                        detail="Corrected block span was not produced by the parser.",
                    )
                )
                continue

            outcome = (
                "exact_match"
                if predicted_block.element_type == gold_block.element_type
                else "incorrect"
            )
            results.append(
                ParserCaseResult(
                    script_id=annotation.script_id,
                    task="block_type_classification",
                    outcome=outcome,
                    scene_number=scene.scene_number,
                    block_key=key,
                    text_excerpt=self._excerpt(gold_block.text),
                    gold_value=gold_block.element_type,
                    predicted_value=predicted_block.element_type,
                    detail=(
                        "Block type matches corrected output."
                        if outcome == "exact_match"
                        else "Block type differs from corrected output."
                    ),
                )
            )

        for key, predicted_block in predicted_blocks.items():
            if key in seen_keys:
                continue
            results.append(
                ParserCaseResult(
                    script_id=annotation.script_id,
                    task="block_type_classification",
                    outcome="extra",
                    scene_number=self._scene_number_from_key(key),
                    block_key=key,
                    text_excerpt=self._excerpt(predicted_block.text),
                    gold_value=None,
                    predicted_value=predicted_block.element_type,
                    detail="Parser produced an extra non-heading block not present in corrected output.",
                )
            )

        return results

    def _evaluate_speakers(
        self,
        annotation: CorrectedScriptAnnotation,
        predicted: ParsedScriptResponse,
    ) -> list[ParserCaseResult]:
        results: list[ParserCaseResult] = []
        predicted_dialogue = self._predicted_dialogue_by_key(predicted)
        gold_dialogue = [
            (scene, block)
            for scene in annotation.corrected_scenes
            for block in scene.blocks
            if block.element_type == "dialogue"
        ]
        seen_keys = set()

        for scene, gold_block in gold_dialogue:
            key = self._block_key(scene.scene_number, gold_block.start_line, gold_block.end_line)
            seen_keys.add(key)
            predicted_block = predicted_dialogue.get(key)
            if predicted_block is None:
                results.append(
                    ParserCaseResult(
                        script_id=annotation.script_id,
                        task="speaker_attribution",
                        outcome="missing",
                        scene_number=scene.scene_number,
                        block_key=key,
                        text_excerpt=self._excerpt(gold_block.text),
                        gold_value=gold_block.speaker,
                        predicted_value=None,
                        detail="Dialogue block was not aligned, so no speaker could be compared.",
                    )
                )
                continue

            outcome = (
                "exact_match"
                if self._normalize(predicted_block.speaker) == self._normalize(gold_block.speaker)
                else "incorrect"
            )
            results.append(
                ParserCaseResult(
                    script_id=annotation.script_id,
                    task="speaker_attribution",
                    outcome=outcome,
                    scene_number=scene.scene_number,
                    block_key=key,
                    text_excerpt=self._excerpt(gold_block.text),
                    gold_value=gold_block.speaker,
                    predicted_value=predicted_block.speaker,
                    detail=(
                        "Speaker matches corrected output."
                        if outcome == "exact_match"
                        else "Speaker differs from corrected output."
                    ),
                )
            )

        for key, predicted_block in predicted_dialogue.items():
            if key in seen_keys:
                continue
            results.append(
                ParserCaseResult(
                    script_id=annotation.script_id,
                    task="speaker_attribution",
                    outcome="extra",
                    scene_number=self._scene_number_from_key(key),
                    block_key=key,
                    text_excerpt=self._excerpt(predicted_block.text),
                    gold_value=None,
                    predicted_value=predicted_block.speaker,
                    detail="Parser produced an extra dialogue block not present in corrected output.",
                )
            )

        return results

    def _summarize(
        self,
        results: list[ParserCaseResult],
        annotation: CorrectedScriptAnnotation,
        predicted: ParsedScriptResponse,
    ) -> list[ParserTaskMetrics]:
        task_order = ("scene_detection", "speaker_attribution", "block_type_classification")
        summary: list[ParserTaskMetrics] = []
        counts = {
            "scene_detection": (
                len(annotation.corrected_scenes),
                len(predicted.scenes),
            ),
            "speaker_attribution": (
                sum(
                    block.element_type == "dialogue"
                    for scene in annotation.corrected_scenes
                    for block in scene.blocks
                ),
                sum(
                    element.element_type == "dialogue"
                    for scene in predicted.scenes
                    for element in scene.elements
                ),
            ),
            "block_type_classification": (
                sum(
                    block.element_type != "scene_heading"
                    for scene in annotation.corrected_scenes
                    for block in scene.blocks
                ),
                sum(
                    element.element_type != "scene_heading"
                    for scene in predicted.scenes
                    for element in scene.elements
                ),
            ),
        }

        for task in task_order:
            task_results = [result for result in results if result.task == task]
            exact = sum(result.outcome == "exact_match" for result in task_results)
            missing = sum(result.outcome == "missing" for result in task_results)
            extra = sum(result.outcome == "extra" for result in task_results)
            incorrect = sum(result.outcome == "incorrect" for result in task_results)
            gold_total, predicted_total = counts[task]
            precision = round(exact / predicted_total, 3) if predicted_total else 0.0
            recall = round(exact / gold_total, 3) if gold_total else 0.0
            exact_rate = round(exact / gold_total, 3) if gold_total else 0.0
            summary.append(
                ParserTaskMetrics(
                    task=task,
                    gold_total=gold_total,
                    predicted_total=predicted_total,
                    exact_match=exact,
                    missing=missing,
                    extra=extra,
                    incorrect=incorrect,
                    precision=precision,
                    recall=recall,
                    exact_match_rate=exact_rate,
                )
            )
        return summary

    def _gold_blocks(
        self,
        annotation: CorrectedScriptAnnotation,
        include_scene_heading: bool,
    ) -> list[Tuple[CorrectedSceneAnnotation, CorrectedBlockAnnotation]]:
        pairs: list[Tuple[CorrectedSceneAnnotation, CorrectedBlockAnnotation]] = []
        for scene in annotation.corrected_scenes:
            for block in scene.blocks:
                if not include_scene_heading and block.element_type == "scene_heading":
                    continue
                pairs.append((scene, block))
        return pairs

    def _predicted_blocks_by_key(
        self,
        predicted: ParsedScriptResponse,
        include_scene_heading: bool,
    ) -> Dict[str, ParsedElement]:
        items: Dict[str, ParsedElement] = {}
        for scene in predicted.scenes:
            for element in scene.elements:
                if not include_scene_heading and element.element_type == "scene_heading":
                    continue
                key = self._block_key(scene.scene_number, element.start_line, element.end_line)
                items[key] = element
        return items

    def _predicted_dialogue_by_key(self, predicted: ParsedScriptResponse) -> Dict[str, ParsedElement]:
        items: Dict[str, ParsedElement] = {}
        for scene in predicted.scenes:
            for element in scene.elements:
                if element.element_type != "dialogue":
                    continue
                key = self._block_key(scene.scene_number, element.start_line, element.end_line)
                items[key] = element
        return items

    def _block_key(self, scene_number: int, start_line: int, end_line: int) -> str:
        return f"{scene_number}:{start_line}-{end_line}"

    def _scene_number_from_key(self, key: str) -> Optional[int]:
        prefix = key.split(":", 1)[0]
        return int(prefix) if prefix.isdigit() else None

    def _scene_signature(self, scene: object) -> str:
        heading = getattr(scene, "heading", None) or "None"
        start_line = getattr(scene, "start_line", None)
        end_line = getattr(scene, "end_line", None)
        return f"{heading} [{start_line}-{end_line}]"

    def _normalize(self, value: Optional[str]) -> str:
        return (value or "").strip().upper()

    def _excerpt(self, text: str) -> str:
        stripped = " ".join(text.split())
        return stripped if len(stripped) <= 80 else f"{stripped[:77]}..."
