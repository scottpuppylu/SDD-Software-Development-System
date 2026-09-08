from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from .core import Orchestrator
from .executor import StageExecutor
from .runner import StageRunner, StageExecutionValidationError
from .context_compiler import CompilationMode


@dataclass
class PipelineRunResult:
    started_at_stage: str
    stopped_at_stage: str
    stop_reason: str
    stages_run: list[dict[str, Any]] = field(default_factory=list)


READINESS_DIMENSIONS = (
    "problem",
    "target_user",
    "mvp_scope",
    "important_behavior_flow",
    "critical_exception_risk_blockers",
    "material_scope_changing_tbd",
    "product_baseline_approval",
)

APPROVED_INTAKE_FORMS = {
    "PLAIN_LANGUAGE",
    "DOCUMENT",
    "IMAGE_OR_UI_REFERENCE",
    "WEBSITE_OR_SYSTEM_REFERENCE",
    "EXISTING_PROGRAM_MODIFICATION",
}

READINESS_RESULTS = {"PASS", "FAIL", "NOT RUN"}
NON_AUTHORITATIVE_SOURCES = {"AI_PROPOSAL", "INFERENCE", "SILENCE"}


class RequirementReadinessError(ValueError):
    """The proposed readiness evaluation is malformed or authority-invalid."""


@dataclass(frozen=True)
class ReadinessDimensionFinding:
    dimension: str
    result: str
    affected_scope: tuple[str, ...]
    evidence_reference: str | None
    authority_reference: str | None
    source_kind: str
    explanation: str = ""
    clarification_question: str | None = None


@dataclass(frozen=True)
class RequirementReadinessRequest:
    intake_form: str
    intake_reference: str
    proposed_baseline_reference: str
    findings: tuple[ReadinessDimensionFinding, ...]
    noncritical_downstream_details: tuple[str, ...] = ()


@dataclass(frozen=True)
class RequirementReadinessDecision:
    result: str
    ready: bool
    findings: tuple[ReadinessDimensionFinding, ...]
    blocked_scope: tuple[str, ...]
    clarification_questions: tuple[str, ...]
    next_route: str
    intake_reference: str
    proposed_baseline_reference: str


class RequirementReadinessEvaluator:
    """Evaluate DES-003 product readiness without creating Product authority."""

    def evaluate(self, request: RequirementReadinessRequest) -> RequirementReadinessDecision:
        if request.intake_form not in APPROVED_INTAKE_FORMS:
            raise RequirementReadinessError("unsupported product intake form")
        if not request.intake_reference or not request.proposed_baseline_reference:
            raise RequirementReadinessError("intake and proposed baseline references are required")

        by_dimension: dict[str, ReadinessDimensionFinding] = {}
        for finding in request.findings:
            if finding.dimension not in READINESS_DIMENSIONS:
                raise RequirementReadinessError(f"unknown readiness dimension: {finding.dimension}")
            if finding.dimension in by_dimension:
                raise RequirementReadinessError(f"duplicate readiness dimension: {finding.dimension}")
            if finding.result not in READINESS_RESULTS:
                raise RequirementReadinessError(
                    f"invalid readiness result for {finding.dimension}: {finding.result}"
                )
            if not finding.affected_scope or not all(finding.affected_scope):
                raise RequirementReadinessError(f"affected scope is required for {finding.dimension}")
            if not finding.explanation:
                raise RequirementReadinessError(
                    f"plain-language explanation is required for {finding.dimension}"
                )
            if finding.result == "PASS":
                if not finding.evidence_reference or not finding.authority_reference:
                    raise RequirementReadinessError(
                        f"PASS requires evidence and authority for {finding.dimension}"
                    )
                if finding.source_kind in NON_AUTHORITATIVE_SOURCES:
                    raise RequirementReadinessError(
                        f"{finding.source_kind} cannot establish {finding.dimension} readiness"
                    )
                if (
                    finding.dimension == "product_baseline_approval"
                    and finding.source_kind != "PRODUCT_AUTHORITY"
                ):
                    raise RequirementReadinessError(
                        "product baseline approval requires Product authority"
                    )
            elif not finding.clarification_question:
                raise RequirementReadinessError(
                    f"focused clarification is required for {finding.dimension}"
                )
            by_dimension[finding.dimension] = finding

        missing = [name for name in READINESS_DIMENSIONS if name not in by_dimension]
        if missing:
            raise RequirementReadinessError(
                "missing readiness dimensions: " + ", ".join(missing)
            )

        ordered = tuple(by_dimension[name] for name in READINESS_DIMENSIONS)
        unresolved = tuple(item for item in ordered if item.result != "PASS")
        blocked_scope = tuple(
            sorted({scope for item in unresolved for scope in item.affected_scope})
        )
        questions = tuple(
            item.clarification_question for item in unresolved if item.clarification_question
        )
        ready = not unresolved
        return RequirementReadinessDecision(
            result="PASS" if ready else "FAIL",
            ready=ready,
            findings=ordered,
            blocked_scope=blocked_scope,
            clarification_questions=questions,
            next_route=(
                "READY_FOR_PRODUCT_BASELINE" if ready else "PRODUCT_CLARIFICATION_REQUIRED"
            ),
            intake_reference=request.intake_reference,
            proposed_baseline_reference=request.proposed_baseline_reference,
        )


class PipelineController:
    """Runs multiple SDD stages without manual artifact copy/paste.

    It deliberately stops before Stage 08 by default because Stage 08 requires
    the Codex/repository coding adapter rather than the authoring reasoning adapter.
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        telemetry_recorder: Any = None,
        *,
        compilation_mode: CompilationMode = CompilationMode.BASELINE,
    ):
        self.orchestrator = orchestrator
        self.runner = StageRunner(
            orchestrator,
            telemetry_recorder=telemetry_recorder,
            compilation_mode=compilation_mode,
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
