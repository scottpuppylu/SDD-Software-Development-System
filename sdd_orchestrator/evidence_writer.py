from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess

from .codex_results import VerificationResult
from .result_serialization import serialize_verification_result
from .task_parser import AtomicTask


def write_stage08_evidence(
    repo_root: Path,
    task: AtomicTask,
    proc: subprocess.CompletedProcess[str],
    changed: list[str],
    verification: list[VerificationResult],
    *,
    status: str,
) -> str:
    evidence_dir = repo_root / ".sdd" / "evidence"
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
        "verification": [
            serialize_verification_result(v)
            for v in verification
        ],
        "codex": {
            "returncode": proc.returncode,
            "final_stdout": proc.stdout,
            "stderr": proc.stderr,
        },
        "recorded_at": stamp,
    }
    (repo_root / rel).write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return rel
