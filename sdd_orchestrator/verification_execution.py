from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Any, Callable, Iterable

from .codex_results import VerificationResult
from .governed_state import ImpactRisk, ModificationImpactLedger
from .verification_policy import VerificationLevel, VerificationPlan, VerificationStep


VERIFICATION_OUTCOMES = frozenset({"PASS", "FAIL", "NOT RUN"})
COVERAGE_STATES = frozenset(
    {"FULL", "PARTIAL", "ABSENT", "STALE", "IRRELEVANT", "NEW_FEATURE_ONLY"}
)


@dataclass(frozen=True)
class LeveledVerificationResult:
    level: VerificationLevel
    result: VerificationResult
    legacy_required: bool = False

    @property
    def passed(self) -> bool:
        return self.result.passed


def execute_local_verification_plan(
    plan: VerificationPlan,
    execute_step: Callable[[VerificationStep], VerificationResult],
) -> tuple[LeveledVerificationResult, ...]:
    """Execute the current local plan without any provider/session dependency."""

    results: list[LeveledVerificationResult] = []
    for step in plan.ordered_steps():
        result = execute_step(step)
        if result.command != step.command:
            raise ValueError("verification result command does not match the authorized step")
        results.append(LeveledVerificationResult(step.level, result, step.legacy_required))
        if not result.passed:
            break
    return tuple(results)


@dataclass(frozen=True)
class RegressionEvidence:
    """Minimum-disclosure evidence metadata used by the coverage projection."""

    identity: str
    result: str
    risk_ids: tuple[str, ...]
    version: str
    purpose: str = "REGRESSION"
    relevant: bool = True
    evidence: str | None = None
    gap: str | None = None

    @property
    def affected_risks(self) -> tuple[str, ...]:
        return self.risk_ids

    def validate(self) -> None:
        if not self.identity or not self.version:
            raise ValueError("evidence identity and version are required")
        if self.result not in VERIFICATION_OUTCOMES:
            raise ValueError(f"invalid verification result: {self.result}")
        if self.purpose not in {"REGRESSION", "NEW_BEHAVIOR"}:
            raise ValueError(f"invalid evidence purpose: {self.purpose}")
        if not self.risk_ids or any(not risk_id for risk_id in self.risk_ids):
            raise ValueError(f"evidence {self.identity} requires affected risk links")
        if len(self.risk_ids) != len(set(self.risk_ids)):
            raise ValueError(f"evidence {self.identity} has duplicate affected risk links")
        if self.result == "NOT RUN" and not self.gap:
            raise ValueError(f"NOT RUN evidence {self.identity} requires an explicit gap")


@dataclass(frozen=True)
class RegressionRisk:
    identity: str
    description: str
    affected_scope: str
    security_related: bool = False


@dataclass(frozen=True)
class RegressionRiskCoverage:
    risk: RegressionRisk
    state: str
    applicable_evidence: tuple[RegressionEvidence, ...]
    nonqualifying_evidence: tuple[RegressionEvidence, ...]
    gaps: tuple[str, ...]


@dataclass(frozen=True)
class RegressionCoverageView:
    modification_id: str
    current_version: str
    state: str
    risk_coverage: tuple[RegressionRiskCoverage, ...]
    new_behavior_evidence: tuple[RegressionEvidence, ...]
    warnings: tuple[str, ...]
    uncovered_risks: tuple[str, ...]
    non_regression_established: bool
    completion_eligible: bool
    stage09_qualification_created: bool = False

    @classmethod
    def computation_failure(
        cls, *, modification_id: str, current_version: str, reason: str
    ) -> "RegressionCoverageView":
        return cls(
            modification_id=modification_id,
            current_version=current_version,
            state="ABSENT",
            risk_coverage=(),
            new_behavior_evidence=(),
            warnings=(f"regression coverage computation failed: {reason}",),
            uncovered_risks=("coverage computation",),
            non_regression_established=False,
            completion_eligible=False,
        )

    @property
    def completion_eligible_projection(self) -> bool:
        return self.completion_eligible


def _ledger_risks(ledger: ModificationImpactLedger) -> tuple[RegressionRisk, ...]:
    risks: list[RegressionRisk] = [
        RegressionRisk(item.identity, item.risk, item.affected_scope, item.high_risk)
        for item in ledger.risks
    ]
    represented_scopes = {risk.affected_scope for risk in risks}
    risks.extend(
        RegressionRisk(scope, f"regression of affected behavior/data: {scope}", scope)
        for scope in ledger.affected_behavior_data
        if scope not in represented_scopes
    )
    identities = [risk.identity for risk in risks]
    if any(not identity for identity in identities) or len(identities) != len(set(identities)):
        raise ValueError("affected risk identities must be nonblank and unique")
    return tuple(risks)


def build_regression_coverage_view(
    ledger: ModificationImpactLedger,
    evidence: Iterable[RegressionEvidence],
    *,
    current_version: str | None = None,
) -> RegressionCoverageView:
    """Project coverage without changing evidence, the ledger, or qualification state."""

    try:
        return _build_regression_coverage_view(
            ledger, evidence, current_version=current_version
        )
    except Exception as exc:
        return RegressionCoverageView.computation_failure(
            modification_id=getattr(ledger, "modification_id", "unknown-modification"),
            current_version=current_version or getattr(ledger, "current_version", ""),
            reason=str(exc),
        )


def _build_regression_coverage_view(
    ledger: ModificationImpactLedger,
    evidence: Iterable[RegressionEvidence],
    *,
    current_version: str | None = None,
) -> RegressionCoverageView:
    ledger.validate()
    version = current_version or ledger.current_version
    if not version:
        raise ValueError("current version is required")
    items = tuple(evidence)
    for item in items:
        item.validate()
    evidence_ids = [item.identity for item in items]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("ambiguous duplicate evidence identity")

    risks = _ledger_risks(ledger)
    known_risks = {risk.identity for risk in risks}
    warnings: list[str] = []
    if ledger.current_version != version or ledger.input_version != version:
        warnings.append(
            "impact ledger is stale for current version "
            f"{version}: input={ledger.input_version}, ledger={ledger.current_version}"
        )

    unknown_links = sorted(
        {risk_id for item in items for risk_id in item.risk_ids if risk_id not in known_risks}
    )
    if unknown_links:
        warnings.append(f"evidence has missing affected-risk links: {unknown_links}")

    coverage: list[RegressionRiskCoverage] = []
    for risk in risks:
        linked = tuple(item for item in items if risk.identity in item.risk_ids)
        applicable = tuple(
            item
            for item in linked
            if item.purpose == "REGRESSION" and item.relevant and item.version == version
        )
        nonqualifying = tuple(item for item in linked if item not in applicable)
        gaps: list[str] = []

        if applicable and all(item.result == "PASS" for item in applicable):
            state = "FULL"
        elif applicable:
            state = "PARTIAL"
            for item in applicable:
                if item.result != "PASS":
                    gaps.append(item.gap or f"{item.identity} result is {item.result}")
        elif any(item.purpose == "REGRESSION" and item.version != version for item in linked):
            state = "STALE"
            gaps.append(f"no current regression evidence for version {version}")
        elif linked and all(
            not item.relevant or item.purpose != "REGRESSION" for item in linked
        ):
            state = "IRRELEVANT"
            gaps.append("linked evidence is irrelevant to regression coverage")
        else:
            state = "ABSENT"
            gaps.append("required regression evidence is absent")

        if state != "FULL":
            sensitivity = "security-related " if risk.security_related else ""
            warnings.append(
                f"{sensitivity}regression risk {risk.identity} is {state}: "
                f"{'; '.join(gaps)} (scope: {risk.affected_scope})"
            )
        coverage.append(
            RegressionRiskCoverage(risk, state, applicable, nonqualifying, tuple(gaps))
        )

    new_behavior = tuple(item for item in items if item.purpose == "NEW_BEHAVIOR")
    states = tuple(item.state for item in coverage)
    current_regression = tuple(
        item
        for item in items
        if item.purpose == "REGRESSION" and item.relevant and item.version == version
    )
    new_behavior_passed = any(
        item.result == "PASS" and item.relevant and item.version == version
        for item in new_behavior
    )
    ledger_is_current = ledger.current_version == version and ledger.input_version == version
    if not ledger_is_current:
        overall_state = "STALE"
    elif states and all(state == "FULL" for state in states):
        overall_state = "FULL"
    elif any(state == "FULL" for state in states) or current_regression:
        overall_state = "PARTIAL"
    elif new_behavior_passed:
        overall_state = "NEW_FEATURE_ONLY"
        warnings.append("new-behavior PASS does not establish non-regression")
    elif states and all(state == "STALE" for state in states):
        overall_state = "STALE"
    elif states and all(state == "ABSENT" for state in states):
        overall_state = "ABSENT"
    else:
        overall_state = "PARTIAL" if states else "ABSENT"

    established = bool(states) and all(state == "FULL" for state in states) and ledger_is_current
    if not risks:
        warnings.append("no affected behavior/data risks are available for regression coverage")
    uncovered = tuple(
        item.risk.identity
        for item in coverage
        if item.state != "FULL" or not ledger_is_current
    ) + tuple(f"missing-link:{risk_id}" for risk_id in unknown_links)
    return RegressionCoverageView(
        modification_id=ledger.modification_id,
        current_version=version,
        state=overall_state,
        risk_coverage=tuple(coverage),
        new_behavior_evidence=new_behavior,
        warnings=tuple(warnings),
        uncovered_risks=uncovered,
        non_regression_established=established,
        completion_eligible=established and not unknown_links,
    )


compute_regression_coverage = build_regression_coverage_view


def execute_verification_command(
    command: str,
    argv: list[str],
    repo_root: Path,
    verify_env: dict[str, str],
    *,
    run_command: Callable[..., Any],
    call_with_heartbeat: Callable[[str, Callable[[], Any]], Any],
    heartbeat_label: str,
) -> VerificationResult:
    try:
        proc = call_with_heartbeat(
            heartbeat_label,
            lambda: run_command(
                argv,
                cwd=repo_root,
                env=verify_env,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
            ),
        )
    except FileNotFoundError as exc:
        return VerificationResult(
            command,
            127,
            "",
            f"verification executable not found: {argv[0]} ({exc})",
        )
    except subprocess.TimeoutExpired as exc:
        return VerificationResult(
            command,
            124,
            str(exc.stdout or ""),
            f"verification timed out: {exc}",
        )
    return VerificationResult(command, proc.returncode, proc.stdout, proc.stderr)
