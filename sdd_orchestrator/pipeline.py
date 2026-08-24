from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .core import Orchestrator
from .executor import StageExecutor
from .runner import StageRunner, StageExecutionValidationError


@dataclass
class PipelineRunResult:
    started_at_stage: str
    stopped_at_stage: str
    stop_reason: str
    stages_run: list[dict[str, Any]] = field(default_factory=list)


class PipelineController:
    """Runs multiple SDD stages without manual artifact copy/paste.

    It deliberately stops before Stage 08 by default because Stage 08 requires
    the Codex/repository coding adapter rather than the authoring reasoning adapter.
    """

    def __init__(self, orchestrator: Orchestrator, telemetry_recorder: Any = None):
        self.orchestrator = orchestrator
        self.runner = StageRunner(
            orchestrator, telemetry_recorder=telemetry_recorder
        )

    def _repository_structure(self, max_entries: int = 500) -> str:
        ignored = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
        entries: list[str] = []
        for path in sorted(self.orchestrator.repo_root.rglob("*")):
            rel = path.relative_to(self.orchestrator.repo_root)
            if any(part in ignored for part in rel.parts):
                continue
            entries.append(rel.as_posix() + ("/" if path.is_dir() else ""))
            if len(entries) >= max_entries:
                entries.append("... [truncated]")
                break
        return "\n".join(entries)

    def _default_semantics(self, stage_id: str) -> dict[str, Any]:
        repo_structure = self._repository_structure()
        defaults: dict[str, dict[str, Any]] = {
            "02": {
                "APPROVED_PRODUCT_DECISIONS": "No additional product decisions beyond the authoritative proposal and user-supplied inputs.",
            },
            "03": {
                "KNOWN_TECHNICAL_CONSTRAINTS_IF_ANY": "No additional technical constraints beyond authoritative artifacts unless explicitly stated there.",
            },
            "04": {
                "REPOSITORY_STRUCTURE_IF_EXISTING": repo_structure,
                "APPROVED_CONSTRAINTS": "Use only constraints explicitly approved in upstream artifacts.",
                "APPROVED_ADRS_IF_ANY": "Use repository ADRs if present; otherwise none.",
            },
            "05": {"REPOSITORY_STRUCTURE": repo_structure},
            "06": {"REPOSITORY_STRUCTURE": repo_structure},
            "07": {
                "REPOSITORY_STRUCTURE": repo_structure,
                "GIT_READINESS": "Derive readiness from repository and Git runtime evidence; do not assume PASS when evidence is absent.",
            },
        }
        return defaults.get(stage_id, {})

    def run_until(
        self,
        executor_factory: Callable[[str], StageExecutor] | StageExecutor,
        *,
        stop_before: str = "08",
        max_stages: int = 20,
        semantic_by_stage: dict[str, dict[str, Any]] | None = None,
    ) -> PipelineRunResult:
        semantic_by_stage = semantic_by_stage or {}
        started = self.orchestrator.current_stage_id
        runs: list[dict[str, Any]] = []

        for _ in range(max_stages):
            sid = self.orchestrator.current_stage_id
            if sid == stop_before.zfill(2):
                return PipelineRunResult(started, sid, "STOP_BEFORE_STAGE", runs)

            semantics = self._default_semantics(sid)
            semantics.update(semantic_by_stage.get(sid, {}))

            executor = executor_factory(sid) if callable(executor_factory) else executor_factory
            run_result = self.runner.run(
                executor,
                sid,
                semantic_inputs=semantics,
            )
            runs.append(run_result)

            transition = run_result.get("transition", {})
            next_value = str(transition.get("next", ""))
            if transition.get("blocked"):
                return PipelineRunResult(started, sid, "BLOCKED", runs)
            if not next_value.isdigit():
                return PipelineRunResult(started, sid, next_value or "STOP", runs)

        return PipelineRunResult(
            started,
            self.orchestrator.current_stage_id,
            "MAX_STAGES_REACHED",
            runs,
        )
