from __future__ import annotations

from pathlib import Path
from typing import Any
import json
import re
import shutil
import subprocess
import threading
import time

import yaml

from .core import Orchestrator
from .codex_cli import CodexCLI
from .codex_results import VerificationResult, CodexTaskRunResult
from .result_serialization import serialize_task_run_result
from .evidence_writer import write_stage08_evidence
from .errors import CodexAdapterError, NoExecutableTaskError
from .verification_policy import VerificationCommandPolicy
from .verification_execution import execute_verification_command
from . import path_scope_policy
from .verification_runtime import (
    build_verification_env,
    resolve_project_python,
    resolve_verification_argv,
)
from .task_parser import AtomicTask, TaskFileParser
from .git_runtime import GitRepository, RecoveryManager, GitRuntimeError




class Stage08CodexRunner:
    RUNTIME_DIRTY_PREFIXES = (".sdd/state/", ".sdd/runs/", ".sdd/evidence/")
    PROTECTED_EXACT = {"AGENTS.md", "tasks.md", "docs/PRD.md", "docs/spec.md", "docs/Design.md"}
    # Stage 08 may write only these .sdd evidence artifacts when an Atomic Task
    # explicitly authorizes the exact path. Governance/runtime control files remain
    # protected even though they also live under .sdd/.
    TASK_WRITABLE_SDD_EXACT = {
        ".sdd/state/implementation-state.md",
        ".sdd/state/post-implementation-verification.md",
    }

    def __init__(
        self,
        orchestrator: Orchestrator,
        *,
        codex: CodexCLI | Any | None = None,
        project_python: str | None = None,
        heartbeat_seconds: int = 30,
    ):
        self.orchestrator = orchestrator
        self.repo_root = orchestrator.repo_root
        self.git = GitRepository(self.repo_root)
        self.recovery = RecoveryManager(self.repo_root)
        self.codex = codex or CodexCLI()
        self.project_python = project_python
        self.heartbeat_seconds = max(0, int(heartbeat_seconds))

    def tasks(self) -> list[AtomicTask]:
        path = self.repo_root / "tasks.md"
        if not path.exists():
            raise CodexAdapterError("tasks.md is missing")
        tasks = TaskFileParser(path.read_text(encoding="utf-8")).parse()
        convergence_root = self.repo_root / ".sdd" / "convergence"
        if convergence_root.exists():
            for item in sorted(convergence_root.glob("TC*.yaml")):
                data = yaml.safe_load(item.read_text(encoding="utf-8")) or {}
                if str(data.get("status", "TODO")).upper() == "DONE":
                    continue
                task_id = str(data.get("task_id", item.stem)).upper()
                raw = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
                tasks.insert(0, AtomicTask(
                    task_id=task_id,
                    title=str(data.get("title", task_id)),
                    status=str(data.get("status", "TODO")).upper(),
                    raw_markdown=raw,
                    traceability=list(data.get("traceability", [])),
                    allowed_paths=list(data.get("allowed_paths", [])),
                    verification_commands=list(data.get("verification_commands", [])),
                ))
        if not tasks:
            raise CodexAdapterError("No Atomic Tasks were parsed from tasks.md")
        return tasks

    def select_task(self, task_id: str | None = None) -> AtomicTask:
        tasks = self.tasks()
        state = self.recovery._load_state()
        requested = task_id or state.get("current_task") or state.get("next_task")
        if requested:
            normalized = TaskFileParser._normalize_task_id(str(requested))
            for task in tasks:
                if task.task_id == normalized:
                    return task
            raise CodexAdapterError(f"Task not found in tasks.md: {requested}")
        for task in tasks:
            if task.status in {"TODO", "IN_PROGRESS"}:
                return task
        raise NoExecutableTaskError("No executable TODO/IN_PROGRESS task remains")

    def preflight(self, task: AtomicTask) -> None:
        check = self.orchestrator.check_required_inputs("08")
        if not check.ready:
            raise CodexAdapterError(
                "Stage 08 entry gate failed: "
                f"missing_files={check.missing_files}, entry_condition_failures={check.entry_condition_failures}"
            )
        authority = self.orchestrator.authority_state
        if authority.get("unresolved_conflicts"):
            raise CodexAdapterError("Stage 08 blocked by unresolved authority conflict")
        if authority.get("blocking_tbds"):
            raise CodexAdapterError("Stage 08 blocked by blocking TBD")
        if not self.git.is_repository():
            raise CodexAdapterError("Stage 08 requires a Git repository")
        if not task.allowed_paths:
            raise CodexAdapterError(
                f"{task.task_id} has no machine-detectable Allowed Paths/Files write scope; return to Stage 06"
            )
        protected = [p for p in task.allowed_paths if self._is_protected(p, task_authorized=True)]
        if protected:
            raise CodexAdapterError(
                f"{task.task_id} attempts to authorize protected authoritative artifacts: {protected}"
            )
        if not task.verification_commands:
            raise CodexAdapterError(
                f"{task.task_id} has no machine-detectable verification command; return to Stage 06"
            )
        for cmd in task.verification_commands:
            VerificationCommandPolicy.argv(cmd)

    def build_prompt(self, task: AtomicTask) -> str:
        trace = ", ".join(task.traceability) if task.traceability else "Use the task's explicit references in tasks.md."
        allowed = "\n".join(f"- {p}" for p in task.allowed_paths)
        verify = "\n".join(f"- {c}" for c in task.verification_commands)
        return f"""You are the Stage 08 coding execution engine inside an SDD governed repository.

Execute exactly one Atomic Task: {task.task_id} — {task.title}

MANDATORY START/RESUME:
1. Read AGENTS.md.
2. Read tasks.md and locate {task.task_id}.
3. Read the PRD/SPEC/DES references relevant to the task.
4. Read .sdd/state/implementation-state.yaml.
5. Inspect git status, current branch, and recent commits.

AUTHORITY BOUNDARY:
- Product Requirement is owned by docs/PRD.md.
- Technical Contract is owned by docs/spec.md.
- Implementation Design is owned by docs/Design.md.
- You may not modify those authoritative artifacts, AGENTS.md, or tasks.md.
- If the task requires an upstream contract/design change or conflicts with authority, STOP and report BLOCKED in your final message. Do not create a workaround.

WRITE SCOPE — do not modify anything outside these paths:
{allowed}

TRACEABILITY:
{trace}

TASK CONTRACT:
{task.raw_markdown}

VERIFICATION EXPECTED BY ORCHESTRATOR:
{verify}

EXECUTION RULES:
- Make the smallest implementation that satisfies the task and authoritative contracts.
- Add/update tests only inside the authorized write scope.
- Do not commit, push, rebase, reset, clean, stash, or amend Git history. The Orchestrator owns checkpointing.
- Do not edit .sdd runtime/configuration files except an exact .sdd evidence path explicitly listed in WRITE SCOPE.
- Do not disable or weaken tests to force green.
- Do not expose secrets or credentials.
- Finish with a concise summary of files changed, validations run, and any blocker/limitation.

BEGIN EXECUTION NOW. Do not merely acknowledge these instructions. Read the repository files, make the authorized T{task.task_id[1:]} changes, and run only the task-scoped checks that are safe inside the Codex sandbox. The Orchestrator will run the declared Verification Commands after you exit.
"""

    def execute_one(self, task_id: str | None = None) -> CodexTaskRunResult:
        task = self.select_task(task_id)
        self.preflight(task)

        before = self.git.snapshot(recent_limit=5)
        relevant_dirty = [
            p for p in before.dirty_paths
            if not self._ignorable_runtime_dirty(p, task.allowed_paths) and not self._generated_verification_dirty(p)
        ]
        unrelated_dirty = [p for p in relevant_dirty if not self._covered(p, task.allowed_paths)]
        if unrelated_dirty:
            raise CodexAdapterError(
                "Repository has pre-existing non-runtime dirty files outside the current task scope; "
                "recover/inspect before Codex execution: " + ", ".join(unrelated_dirty)
            )

        reconciled = self._reconcile_head_checkpoint(task, before.head_commit)
        if reconciled is not None:
            return reconciled

        # A prior attempt of the same Atomic Task may have produced authorized
        # files and then failed verification. Those dirty files are resumable
        # task state, not unrelated work. Re-run Codex so it can inspect/fix the
        # task, then verify the complete current task scope.
        self._progress(f"Starting {task.task_id} — {task.title}")
        self._progress(f"{task.task_id} Codex started")
        proc = self._call_with_heartbeat(
            f"{task.task_id} Codex still running",
            lambda: self.codex.execute(self.repo_root, self.build_prompt(task)),
        )
        self._progress(f"{task.task_id} Codex completed (exit={proc.returncode})")
        after = self.git.snapshot(recent_limit=5)
        post_nonruntime_dirty = [
            p for p in after.dirty_paths
            if not self._ignorable_runtime_dirty(p, task.allowed_paths) and not self._generated_verification_dirty(p)
        ]
        post_unauthorized = [p for p in post_nonruntime_dirty if not self._covered(p, task.allowed_paths)]
        post_protected = [
            p for p in post_nonruntime_dirty
            if self._is_protected(p, task_authorized=self._covered(p, task.allowed_paths))
        ]
        if post_unauthorized or post_protected:
            raise CodexAdapterError(
                "Codex write-scope violation detected. "
                f"unauthorized={post_unauthorized}, protected={post_protected}. "
                "Changes are left uncommitted for inspection."
            )
        changed = sorted(post_nonruntime_dirty)

        if proc.returncode != 0:
            return self._finish_without_checkpoint(task, proc, changed, "CODEX_FAILED")
        if not changed:
            return self._finish_without_checkpoint(task, proc, changed, "NO_CHANGES")

        self._progress(f"{task.task_id} verification started")
        verification = self._run_verification(task)
        if not all(v.passed for v in verification):
            evidence = self._write_evidence(task, proc, changed, verification, status="VERIFICATION_FAILED")
            self._progress(f"{task.task_id} verification FAILED")
            return CodexTaskRunResult(
                task.task_id, task.title, proc.returncode, proc.stdout, proc.stderr,
                changed, verification, None, self._next_task_id(task.task_id),
                "VERIFICATION_FAILED", evidence,
            )

        self._progress(f"{task.task_id} verification PASS")
        # T014 is an evidence-index task. Codex may draft its Markdown before the
        # Orchestrator has run the declared Verification Commands, so its prose is
        # provisional. Finalize task-authorized evidence indexes from machine/runtime
        # results before checkpointing; Stage 09 remains the owner of PASS/FAIL.
        if task.task_id == "T014":
            self._finalize_t014_evidence_indexes(task, verification)
            after_finalize = self.git.snapshot(recent_limit=5)
            changed = sorted(
                p for p in after_finalize.dirty_paths
                if not self._ignorable_runtime_dirty(p, task.allowed_paths)
                and not self._generated_verification_dirty(p)
                and self._covered(p, task.allowed_paths)
            )
        evidence = self._write_evidence(task, proc, changed, verification, status="PASS")
        checkpoint_paths = changed + [evidence]
        commit = self.git.checkpoint(
            task_id=task.task_id,
            summary=task.title,
            paths=checkpoint_paths,
            commit_type="feat" if not task.task_id.startswith("TC") else "fix",
            scope="implementation",
            allow_unrelated_dirty=True,  # runtime state files are orchestrator-managed
        )
        next_task = self._next_task_id(task.task_id)
        self.recovery.record_checkpoint(
            commit=commit,
            completed_task=task.task_id,
            next_task=next_task,
            test_status="PASS",
        )
        self._mark_convergence_done(task.task_id)
        self._progress(f"{task.task_id} checkpoint {commit}")
        if next_task:
            self._progress(f"Next task: {next_task}")
        return CodexTaskRunResult(
            task.task_id, task.title, proc.returncode, proc.stdout, proc.stderr,
            changed, verification, commit, next_task, "DONE", evidence,
        )

    def _reconcile_head_checkpoint(
        self, task: AtomicTask, head_commit: str | None
    ) -> CodexTaskRunResult | None:
        """Repair state only when HEAD itself proves a completed Stage 08 task."""
        if not head_commit:
            return None
        subject = self.git.commit_subject(head_commit)
        match = re.match(
            r"^(?:feat|fix)\(implementation\): \[([A-Z]+\d+)\] .+", subject
        )
        if not match or match.group(1) != task.task_id:
            return None

        checkpoint_paths = self.git.commit_paths(head_commit)
        evidence_paths = [
            path for path in checkpoint_paths
            if path.startswith(".sdd/evidence/")
            and path.endswith(f"-{task.task_id}.json")
        ]
        if len(evidence_paths) != 1:
            return None
        try:
            evidence = json.loads(
                self.git.read_committed_file(evidence_paths[0], head_commit)
            )
        except json.JSONDecodeError:
            return None
        if not isinstance(evidence, dict):
            return None
        verification_data = evidence.get("verification")
        codex_data = evidence.get("codex")
        if (
            evidence.get("schema_version") != "1.0"
            or evidence.get("stage") != "08"
            or evidence.get("task_id") != task.task_id
            or evidence.get("status") != "PASS"
            or not isinstance(evidence.get("changed_paths"), list)
            or not isinstance(codex_data, dict)
            or codex_data.get("returncode") != 0
            or not isinstance(verification_data, list)
            or not verification_data
            or any(
                not isinstance(item, dict)
                or not isinstance(item.get("command"), str)
                or not isinstance(item.get("returncode"), int)
                or not isinstance(item.get("stdout"), str)
                or not isinstance(item.get("stderr"), str)
                or item.get("passed") is not True
                or item.get("returncode") != 0
                for item in verification_data
            )
            or [item["command"] for item in verification_data]
            != task.verification_commands
        ):
            return None

        verification = [
            VerificationResult(
                command=str(item["command"]),
                returncode=int(item.get("returncode", 0)),
                stdout=str(item.get("stdout", "")),
                stderr=str(item.get("stderr", "")),
            )
            for item in verification_data
        ]
        next_task = self._next_task_id(task.task_id)
        state = self.recovery._load_state()
        already_recorded = (
            state.get("last_completed_task") == task.task_id
            and state.get("last_verified_commit") == head_commit
            and state.get("current_task") == next_task
            and state.get("next_task") is None
            and state.get("test_status", {}).get("overall") == "PASS"
        )
        if not already_recorded:
            self.recovery.record_checkpoint(
                commit=head_commit,
                completed_task=task.task_id,
                next_task=next_task,
                test_status="PASS",
            )
        self._progress(f"{task.task_id} reconciled from checkpoint {head_commit}")
        return CodexTaskRunResult(
            task.task_id,
            task.title,
            int(codex_data.get("returncode", 0)),
            str(codex_data.get("final_stdout", "")),
            str(codex_data.get("stderr", "")),
            list(evidence["changed_paths"]),
            verification,
            head_commit,
            next_task,
            "DONE",
            evidence_paths[0],
        )

    def run_until_complete(self, *, max_tasks: int = 100) -> dict[str, Any]:
        results: list[CodexTaskRunResult] = []
        for _ in range(max_tasks):
            try:
                task = self.select_task()
            except NoExecutableTaskError:
                break
            result = self.execute_one(task.task_id)
            results.append(result)
            if result.status != "DONE":
                return {
                    "stage": "08",
                    "status": "BLOCKED",
                    "reason": result.status,
                    "tasks": [self._serialize_result(r) for r in results],
                }
            # Do not depend on tasks.md status mutation; implementation-state drives next task.
            if result.next_task is None:
                break

        if len(results) >= max_tasks and results and results[-1].next_task:
            last = results[-1]
            self._progress("SAFE TO STOP")
            self._progress(f"Last completed: {last.task_id}")
            self._progress(f"Next task: {last.next_task}")
            return {
                "stage": "08",
                "status": "SAFE_STOP",
                "safe_to_stop": True,
                "last_completed_task": last.task_id,
                "next_task": last.next_task,
                "tasks": [self._serialize_result(r) for r in results],
            }

        # Stage 08 execution completed. Transition to Stage 09 is deterministic;
        # conformance is NOT asserted here.
        transition = self._advance_stage_08_to_09()
        return {
            "stage": "08",
            "status": "COMPLETED",
            "tasks": [self._serialize_result(r) for r in results],
            "transition": transition,
        }

    def _resolve_project_python(self) -> str:
        return resolve_project_python(self.repo_root, self.project_python)

    @staticmethod
    def _verification_env(project_python: str) -> dict[str, str]:
        return build_verification_env(project_python)

    def _run_verification(self, task: AtomicTask) -> list[VerificationResult]:
        results: list[VerificationResult] = []
        project_python = self._resolve_project_python()
        verify_env = self._verification_env(project_python)
        for command in task.verification_commands:
            self._progress(f"{task.task_id} verify: {command}")
            argv = VerificationCommandPolicy.argv(command)
            argv = resolve_verification_argv(
                argv, project_python, verify_env, resolver=shutil.which
            )
            result = execute_verification_command(
                command,
                argv,
                self.repo_root,
                verify_env,
                run_command=subprocess.run,
                call_with_heartbeat=self._call_with_heartbeat,
                heartbeat_label=f"{task.task_id} verification still running",
            )
            results.append(result)
            self._progress(f"{task.task_id} verify {'PASS' if result.passed else 'FAIL'}: {command}")
            if not result.passed:
                break
        return results


    def _finalize_t014_evidence_indexes(
        self, task: AtomicTask, verification: list[VerificationResult]
    ) -> list[str]:
        """Finalize T014 Markdown from runtime evidence, never provider narrative.

        These files are Stage 08 evidence indexes, not Stage 09 decisions. The
        Orchestrator owns command execution evidence; Codex text written before
        those commands is only a draft and must not contradict the actual results.
        """
        authorized = {p for p in task.allowed_paths if p in self.TASK_WRITABLE_SDD_EXACT}
        if not authorized:
            return []
        overall = "PASS" if verification and all(v.passed for v in verification) else "INCOMPLETE"
        commands = "\n".join(
            f"- `{v.command}` — return code `{v.returncode}` — {'PASS' if v.passed else 'FAIL'}"
            for v in verification
        ) or "- No runtime verification commands were recorded."
        state = self.recovery._load_state()
        prior = state.get("last_completed_task")
        generated = {
            ".sdd/state/implementation-state.md": f"""# Implementation State Evidence

<!-- SDD-RUNTIME-FINALIZED:T014 -->

- Evidence owner: Stage 08 Orchestrator runtime
- T014 runtime verification: `{overall}`
- Prior completed task before T014 finalization: `{prior or 'UNKNOWN'}`
- T014 completion becomes authoritative only after the Orchestrator creates the task checkpoint and updates `implementation-state.yaml`.

## Runtime Verification Commands

{commands}

This file records execution evidence only. It does not make the Stage 09 Verification Decision.
""",
            ".sdd/state/post-implementation-verification.md": f"""# Post-Implementation Verification Evidence Index

<!-- SDD-RUNTIME-FINALIZED:T014 -->

- Stage 08 task: `T014`
- Runtime verification result: `{overall}`
- Evidence source: Orchestrator-executed declared Verification Commands
- Provider/Codex narrative written before these commands is provisional and is not runtime execution authority.

## Recorded Commands

{commands}

## Authority Boundary

This index reports Stage 08 runtime evidence. It does **not** declare Stage 09 `PASS | FAIL | INCOMPLETE`; Stage 09 owns that decision using Product, Technical, Design, code, tests, Git, and this runtime evidence.
""",
        }
        written=[]
        for rel,text in generated.items():
            if rel not in authorized:
                continue
            path=self.repo_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                path.write_text(text, encoding="utf-8")
                written.append(rel)
        return written

    def _write_evidence(
        self,
        task: AtomicTask,
        proc: subprocess.CompletedProcess[str],
        changed: list[str],
        verification: list[VerificationResult],
        *,
        status: str,
    ) -> str:
        return write_stage08_evidence(
            self.repo_root,
            task,
            proc,
            changed,
            verification,
            status=status,
        )

    def _finish_without_checkpoint(
        self,
        task: AtomicTask,
        proc: subprocess.CompletedProcess[str],
        changed: list[str],
        status: str,
    ) -> CodexTaskRunResult:
        evidence = self._write_evidence(task, proc, changed, [], status=status)
        return CodexTaskRunResult(
            task.task_id, task.title, proc.returncode, proc.stdout, proc.stderr,
            changed, [], None, self._next_task_id(task.task_id), status, evidence,
        )

    def _mark_convergence_done(self, task_id: str) -> None:
        if not task_id.startswith("TC"):
            return
        path = self.repo_root / ".sdd" / "convergence" / f"{task_id}.yaml"
        if not path.exists():
            return
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        data["status"] = "DONE"
        path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")

    def _next_task_id(self, current_id: str) -> str | None:
        tasks = self.tasks()
        found = False
        for task in tasks:
            if found and task.status in {"TODO", "IN_PROGRESS"}:
                return task.task_id
            if task.task_id == current_id:
                found = True
        return None

    def _advance_stage_08_to_09(self) -> dict[str, Any]:
        state = self.orchestrator.project_state
        state["stages"]["08"]["status"] = "DONE"
        state["stages"]["08"]["result"] = "COMPLETED"
        state["lifecycle"]["last_completed_stage"] = "08"
        state["lifecycle"]["current_stage"] = "09"
        state["lifecycle"]["current_stage_name"] = self.orchestrator.get_stage("09")["name"]
        state["lifecycle"]["next_action"] = "RUN_STAGE"
        state["stages"]["09"]["status"] = "IN_PROGRESS"
        self.orchestrator._save_yaml(self.orchestrator.project_state_path, state)
        return {"stage_id": "08", "result": "COMPLETED", "next": "09"}

    def _generated_verification_dirty(self, path: str) -> bool:
        return path_scope_policy.generated_verification_dirty(
            path,
            is_tracked=self.git.is_tracked,
        )

    @classmethod
    def _runtime_dirty(cls, path: str) -> bool:
        return path_scope_policy.runtime_dirty(path, cls.RUNTIME_DIRTY_PREFIXES)

    @classmethod
    def _ignorable_runtime_dirty(cls, path: str, allowed_paths: list[str]) -> bool:
        # Runtime files are normally orchestrator-owned noise. When Stage 06 has
        # explicitly authorized a task-writable evidence artifact, however, it is
        # real task output and must participate in scope review + checkpointing.
        return path_scope_policy.ignorable_runtime_dirty(
            path,
            allowed_paths,
            runtime_dirty_prefixes=cls.RUNTIME_DIRTY_PREFIXES,
            task_writable_sdd_exact=cls.TASK_WRITABLE_SDD_EXACT,
        )

    @classmethod
    def _is_protected(cls, path: str, *, task_authorized: bool = False) -> bool:
        return path_scope_policy.is_protected(
            path,
            task_authorized=task_authorized,
            protected_exact=cls.PROTECTED_EXACT,
            task_writable_sdd_exact=cls.TASK_WRITABLE_SDD_EXACT,
        )

    @staticmethod
    def _progress(message: str) -> None:
        print(f"[Stage 08] {message}", flush=True)

    def _call_with_heartbeat(self, label: str, operation):
        if self.heartbeat_seconds <= 0:
            return operation()
        stop = threading.Event()
        started = time.monotonic()

        def beat() -> None:
            while not stop.wait(self.heartbeat_seconds):
                elapsed = int(time.monotonic() - started)
                self._progress(f"{label} ({elapsed}s elapsed)")

        thread = threading.Thread(target=beat, name="sdd-stage08-heartbeat", daemon=True)
        thread.start()
        try:
            return operation()
        finally:
            stop.set()
            thread.join(timeout=1)

    @staticmethod
    def _covered(path: str, allowed_paths: list[str]) -> bool:
        return path_scope_policy.covered(path, allowed_paths)

    @staticmethod
    def _serialize_result(result: CodexTaskRunResult) -> dict[str, Any]:
        return serialize_task_run_result(result)
