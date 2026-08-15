from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import time

import yaml

from .core import Orchestrator
from .errors import CodexAdapterError
from .verification_policy import VerificationCommandPolicy
from .task_parser import AtomicTask, TaskFileParser
from .git_runtime import GitRepository, RecoveryManager, GitRuntimeError




@dataclass
class VerificationResult:
    command: str
    returncode: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.returncode == 0


@dataclass
class CodexTaskRunResult:
    task_id: str
    title: str
    codex_returncode: int
    codex_stdout: str
    codex_stderr: str
    changed_paths: list[str]
    verification: list[VerificationResult]
    checkpoint_commit: str | None
    next_task: str | None
    status: str
    evidence_file: str | None


class CodexCLI:
    def __init__(
        self,
        *,
        executable: str = "codex",
        sandbox: str = "workspace-write",
        approval_policy: str = "never",
        timeout_seconds: int = 1800,
        ephemeral: bool = True,
    ):
        self.executable = executable
        self.sandbox = sandbox
        self.approval_policy = approval_policy
        self.timeout_seconds = timeout_seconds
        self.ephemeral = ephemeral

    def resolved_executable(self) -> str | None:
        resolved = shutil.which(self.executable)
        if resolved:
            return resolved
        if os.name == "nt" and not self.executable.lower().endswith((".cmd", ".exe", ".bat")):
            return shutil.which(self.executable + ".cmd")
        return None

    def available(self) -> bool:
        return self.resolved_executable() is not None

    def command(self, prompt: str, *, executable: str | None = None) -> list[str]:
        # `codex exec` is the non-interactive execution surface. Pass the
        # Stage 08 prompt through forced UTF-8 stdin (`codex exec -`) instead
        # of as a positional argv value. This avoids Windows multiline/large
        # prompt transport issues and follows Codex's documented stdin mode.
        # The `prompt` parameter remains in the signature for compatibility;
        # its content is supplied by `execute()` via subprocess stdin.
        cmd = [
            executable or self.executable,
            "exec",
            "--sandbox",
            self.sandbox,
        ]
        if self.ephemeral:
            cmd.append("--ephemeral")
        cmd.append("-")
        return cmd

    def execute(self, repo_root: Path, prompt: str) -> subprocess.CompletedProcess[str]:
        executable = self.resolved_executable()
        if not executable:
            raise CodexAdapterError(
                "Codex CLI is not installed or not on PATH. Install/authenticate Codex before Stage 08 execution."
            )
        return subprocess.run(
            self.command(prompt, executable=executable),
            cwd=repo_root,
            input=prompt,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=self.timeout_seconds,
        )


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
        raise CodexAdapterError("No executable TODO/IN_PROGRESS task remains")

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

    def run_until_complete(self, *, max_tasks: int = 100) -> dict[str, Any]:
        results: list[CodexTaskRunResult] = []
        for _ in range(max_tasks):
            try:
                task = self.select_task()
            except CodexAdapterError as exc:
                if "No executable TODO/IN_PROGRESS task remains" in str(exc):
                    break
                raise
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
        candidates: list[str] = []
        if self.project_python:
            candidates.append(self.project_python)
        env_python = os.environ.get("SDD_PROJECT_PYTHON")
        if env_python:
            candidates.append(env_python)

        if os.name == "nt":
            candidates.append(str(self.repo_root / ".venv" / "Scripts" / "python.exe"))
        else:
            candidates.append(str(self.repo_root / ".venv" / "bin" / "python"))

        # Backward-compatible final fallback. It is acceptable only if the
        # project itself accepts the Orchestrator interpreter; project package
        # metadata/verification will reject an incompatible runtime.
        candidates.append(sys.executable)

        for candidate in candidates:
            if not candidate:
                continue
            p = Path(candidate)
            if p.is_absolute() and p.exists():
                return str(p)
            resolved = shutil.which(candidate)
            if resolved:
                return resolved
        raise CodexAdapterError(
            "No project Python interpreter is available. Supply --project-python <path> "
            "or set SDD_PROJECT_PYTHON to the project's Python executable."
        )

    @staticmethod
    def _verification_env(project_python: str) -> dict[str, str]:
        env = os.environ.copy()
        py = Path(project_python)
        prepend: list[str] = [str(py.parent)]
        if os.name == "nt":
            scripts = py.parent / "Scripts"
            if scripts.exists():
                prepend.append(str(scripts))
        env["PATH"] = os.pathsep.join(prepend + [env.get("PATH", "")])
        env["SDD_PROJECT_PYTHON"] = project_python
        return env

    def _run_verification(self, task: AtomicTask) -> list[VerificationResult]:
        results: list[VerificationResult] = []
        project_python = self._resolve_project_python()
        verify_env = self._verification_env(project_python)
        for command in task.verification_commands:
            self._progress(f"{task.task_id} verify: {command}")
            argv = VerificationCommandPolicy.argv(command)
            # Python verification belongs to the project runtime, not to the
            # SDD Orchestrator's own interpreter. This allows SDD to run on one
            # Python minor while verifying a repository governed by another.
            if argv[0] in {"python", "python3"}:
                argv[0] = project_python
            elif argv[0] == "pytest":
                argv = [project_python, "-m", "pytest", *argv[1:]]
            else:
                # Windows CreateProcess does not reliably apply PATHEXT when
                # shell=False. Resolve project-installed console scripts (for
                # example ``todo`` -> ``...\Scripts\todo.exe``) ourselves
                # against the verification environment before execution.
                resolved = shutil.which(argv[0], path=verify_env.get("PATH"))
                if resolved:
                    argv[0] = resolved
            try:
                proc = self._call_with_heartbeat(
                    f"{task.task_id} verification still running",
                    lambda: subprocess.run(
                        argv,
                        cwd=self.repo_root,
                        env=verify_env,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        capture_output=True,
                    ),
                )
            except FileNotFoundError as exc:
                results.append(
                    VerificationResult(
                        command,
                        127,
                        "",
                        f"verification executable not found: {argv[0]} ({exc})",
                    )
                )
                break
            results.append(VerificationResult(command, proc.returncode, proc.stdout, proc.stderr))
            self._progress(f"{task.task_id} verify {'PASS' if proc.returncode == 0 else 'FAIL'}: {command}")
            if proc.returncode != 0:
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
        evidence_dir = self.repo_root / ".sdd" / "evidence"
        evidence_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
        rel = f".sdd/evidence/{stamp}-{task.task_id}.json"
        payload = {
            "schema_version": "1.0",
            "stage": "08",
            "task_id": task.task_id,
            "title": task.title,
            "status": status,
            "changed_paths": changed,
            "verification": [asdict(v) | {"passed": v.passed} for v in verification],
            "codex": {
                "returncode": proc.returncode,
                "final_stdout": proc.stdout,
                "stderr": proc.stderr,
            },
            "recorded_at": stamp,
        }
        (self.repo_root / rel).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return rel

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
        """Ignore only untracked, safely reproducible Python verification artifacts.

        Tracked files are never ignored, even when their names match these patterns.
        This keeps task scope enforcement strict while allowing editable installs and
        imports to leave normal build/cache byproducts between atomic task attempts.
        """
        normalized = path.replace("\\", "/")
        parts = normalized.split("/")
        generated = (
            any(part == "__pycache__" for part in parts)
            or normalized.endswith(".pyc")
            or any(part.endswith(".egg-info") for part in parts)
        )
        return generated and not self.git.is_tracked(path)

    @classmethod
    def _runtime_dirty(cls, path: str) -> bool:
        return path.startswith(cls.RUNTIME_DIRTY_PREFIXES)

    @classmethod
    def _ignorable_runtime_dirty(cls, path: str, allowed_paths: list[str]) -> bool:
        # Runtime files are normally orchestrator-owned noise. When Stage 06 has
        # explicitly authorized a task-writable evidence artifact, however, it is
        # real task output and must participate in scope review + checkpointing.
        if path in cls.TASK_WRITABLE_SDD_EXACT and cls._covered(path, allowed_paths):
            return False
        return cls._runtime_dirty(path)

    @classmethod
    def _is_protected(cls, path: str, *, task_authorized: bool = False) -> bool:
        if path in cls.PROTECTED_EXACT or path.startswith("docs/handoff/"):
            return True
        if path.startswith(".sdd/"):
            return not (task_authorized and path in cls.TASK_WRITABLE_SDD_EXACT)
        return False

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
        for allowed in allowed_paths:
            normalized = allowed.rstrip("/")
            if "*" in normalized or "?" in normalized or "[" in normalized:
                import fnmatch
                if fnmatch.fnmatch(path, normalized):
                    return True
            elif path == normalized or path.startswith(normalized + "/"):
                return True
        return False

    @staticmethod
    def _serialize_result(result: CodexTaskRunResult) -> dict[str, Any]:
        data = asdict(result)
        for item in data.get("verification", []):
            item["passed"] = item.get("returncode") == 0
        return data
