from __future__ import annotations

import argparse
import json
from dataclasses import asdict, is_dataclass
from pathlib import Path

from .core import Orchestrator, SDDOrchestratorError
from .runner import StageRunner
from .executor import ExternalCommandExecutor
from .pipeline import PipelineController
from .providers import CodexExecReasoningExecutor, OpenAIResponsesExecutor, ReasoningProviderError
from .git_runtime import GitRepository, RecoveryManager, GitRuntimeError
from .codex_adapter import Stage08CodexRunner, CodexCLI, CodexAdapterError
from .decisions import DecisionGateway, DecisionGatewayError
from .system_controller import FullSystemController
from .telemetry.recorder import TelemetryRecorder


def _print(data):
    if is_dataclass(data):
        data = asdict(data)
    elif hasattr(data, "__dict__"):
        data = data.__dict__
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _semantic_dict(items: list[str]) -> dict[str, str]:
    result = {}
    for item in items:
        if "=" in item:
            key, value = item.split("=", 1)
        else:
            key, value = item, "AVAILABLE"
        result[key] = value
    return result


def _semantic_by_stage(items: list[str]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for item in items:
        if ":" not in item or "=" not in item:
            raise SystemExit("Pipeline semantic format must be STAGE:KEY=VALUE")
        stage, rest = item.split(":", 1)
        key, value = rest.split("=", 1)
        result.setdefault(stage.zfill(2), {})[key] = value
    return result


def main():
    parser = argparse.ArgumentParser(prog="sdd")
    parser.add_argument("--repo", default=".", help="Repository root")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("status")
    sub.add_parser("current")

    p_check = sub.add_parser("check")
    p_check.add_argument("--stage")
    p_check.add_argument("--semantic", action="append", default=[])

    p_packet = sub.add_parser("packet")
    p_packet.add_argument("--stage")
    p_packet.add_argument("--semantic", action="append", default=[])

    p_run = sub.add_parser("run")
    p_run.add_argument("--stage")
    group = p_run.add_mutually_exclusive_group(required=True)
    group.add_argument("--executor-command")
    group.add_argument("--codex", action="store_true")
    group.add_argument("--openai", action="store_true")
    p_run.add_argument("--model")
    p_run.add_argument("--codex-bin", default="codex")
    p_run.add_argument("--semantic", action="append", default=[])

    p_pipe = sub.add_parser("pipeline")
    p_pipe.add_argument("--provider", choices=["codex", "openai", "command"], default="codex")
    p_pipe.add_argument("--executor-command")
    p_pipe.add_argument("--model")
    p_pipe.add_argument("--codex-bin", default="codex")
    p_pipe.add_argument("--stop-before", default="08")
    p_pipe.add_argument("--max-stages", type=int, default=20)
    p_pipe.add_argument("--semantic", action="append", default=[], help="STAGE:KEY=VALUE")

    p_result = sub.add_parser("record-result")
    p_result.add_argument("stage")
    p_result.add_argument("result")
    p_result.add_argument("--classification")

    p_route = sub.add_parser("route-conflict")
    p_route.add_argument("domains", nargs="+")

    sub.add_parser("git-status")
    sub.add_parser("recovery")

    p_checkpoint = sub.add_parser("checkpoint")
    p_checkpoint.add_argument("--task", required=True)
    p_checkpoint.add_argument("--summary", required=True)
    p_checkpoint.add_argument("--path", action="append", default=[], required=True)
    p_checkpoint.add_argument("--type", default="chore")
    p_checkpoint.add_argument("--scope", default="sdd")
    p_checkpoint.add_argument("--allow-unrelated-dirty", action="store_true")
    p_checkpoint.add_argument("--next-task")
    p_checkpoint.add_argument("--test-status", default="PASS")

    p_codex = sub.add_parser("codex-task")
    p_codex.add_argument("--task")
    p_codex.add_argument("--codex-bin", default="codex")
    p_codex.add_argument("--timeout", type=int, default=1800)
    p_codex.add_argument("--project-python")
    p_codex.add_argument("--heartbeat-seconds", type=int, default=30)

    p_codex_stage = sub.add_parser("codex-stage08")
    p_codex_stage.add_argument("--codex-bin", default="codex")
    p_codex_stage.add_argument("--timeout", type=int, default=1800)
    p_codex_stage.add_argument("--max-tasks", type=int, default=100)
    p_codex_stage.add_argument("--project-python")
    p_codex_stage.add_argument("--heartbeat-seconds", type=int, default=30)

    p_decision_create = sub.add_parser("decision-create")
    p_decision_create.add_argument("--type", required=True)
    p_decision_create.add_argument("--source-stage", required=True)
    p_decision_create.add_argument("--domain", action="append", required=True)
    p_decision_create.add_argument("--question", required=True)
    p_decision_create.add_argument("--context", default="")
    p_decision_create.add_argument("--option", action="append", default=[])
    p_decision_create.add_argument("--risk", default="MEDIUM")
    p_decision_create.add_argument("--artifact", action="append", default=[])

    p_decision_list = sub.add_parser("decision-list")
    p_decision_list.add_argument("--status")

    p_decision_show = sub.add_parser("decision-show")
    p_decision_show.add_argument("decision_id")

    p_decision_resolve = sub.add_parser("decision-resolve")
    p_decision_resolve.add_argument("decision_id")
    p_decision_resolve.add_argument("--resolution", required=True)
    p_decision_resolve.add_argument("--note")

    p_auto = sub.add_parser("auto")
    p_auto.add_argument("--reasoning-provider", choices=["codex", "openai"], default="codex")
    p_auto.add_argument("--model")
    p_auto.add_argument("--codex-bin", default="codex")
    p_auto.add_argument("--max-steps", type=int, default=100)
    p_auto.add_argument("--project-python", help="Python executable used for Stage 08 project verification")
    p_auto.add_argument("--heartbeat-seconds", type=int, default=30, help="Stage 08 heartbeat interval; 0 disables")
    p_auto.add_argument("--semantic", action="append", default=[], help="STAGE:KEY=VALUE")

    args = parser.parse_args()
    repo = Path(args.repo)

    if args.command == "git-status":
        _print(GitRepository(repo).snapshot())
        return
    if args.command == "recovery":
        _print(RecoveryManager(repo).snapshot())
        return
    if args.command == "auto":
        orch = Orchestrator(repo)
        telemetry_recorder = TelemetryRecorder.from_environment(repo)
        reasoning = (
            CodexExecReasoningExecutor(
                executable=args.codex_bin,
                model=args.model,
                repo_root=repo,
                telemetry_recorder=telemetry_recorder,
            )
            if args.reasoning_provider == "codex"
            else OpenAIResponsesExecutor(
                model=args.model or "gpt-5.6",
                telemetry_recorder=telemetry_recorder,
            )
        )
        codex_runner = Stage08CodexRunner(
            orch,
            codex=CodexCLI(executable=args.codex_bin),
            project_python=args.project_python,
            heartbeat_seconds=args.heartbeat_seconds,
        )
        controller = FullSystemController(
            orch,
            reasoning,
            codex_runner,
            telemetry_recorder=telemetry_recorder,
        )
        _print(controller.run(max_steps=args.max_steps, semantic_by_stage=_semantic_by_stage(args.semantic)))
        return
    if args.command.startswith("decision-"):
        orch = Orchestrator(repo)
        gateway = DecisionGateway(orch)
        if args.command == "decision-create":
            _print(gateway.create(
                decision_type=args.type,
                source_stage=args.source_stage,
                authority_domains=args.domain,
                question=args.question,
                context=args.context,
                options=args.option,
                risk=args.risk,
                affected_artifacts=args.artifact,
            ))
        elif args.command == "decision-list":
            _print(gateway.list(status=args.status))
        elif args.command == "decision-show":
            _print(gateway.get(args.decision_id))
        elif args.command == "decision-resolve":
            _print(gateway.resolve(args.decision_id, resolution=args.resolution, note=args.note))
        return
    if args.command in {"codex-task", "codex-stage08"}:
        orch = Orchestrator(repo)
        codex = CodexCLI(executable=args.codex_bin, timeout_seconds=args.timeout)
        stage08 = Stage08CodexRunner(
            orch,
            codex=codex,
            project_python=args.project_python,
            heartbeat_seconds=args.heartbeat_seconds,
        )
        if args.command == "codex-task":
            _print(stage08.execute_one(args.task))
        else:
            _print(stage08.run_until_complete(max_tasks=args.max_tasks))
        return
    if args.command == "checkpoint":
        git = GitRepository(repo)
        commit = git.checkpoint(
            task_id=args.task,
            summary=args.summary,
            paths=args.path,
            commit_type=args.type,
            scope=args.scope,
            allow_unrelated_dirty=args.allow_unrelated_dirty,
        )
        recovery = RecoveryManager(repo)
        recovery.record_checkpoint(
            commit=commit,
            completed_task=args.task,
            next_task=args.next_task,
            test_status=args.test_status,
        )
        _print({"checkpoint_commit": commit, "task": args.task, "next_task": args.next_task})
        return

    orch = Orchestrator(repo)
    telemetry_recorder = TelemetryRecorder.from_environment(repo)
    runner = StageRunner(orch, telemetry_recorder=telemetry_recorder)

    if args.command == "status":
        _print(orch.status())
    elif args.command == "current":
        _print(orch.stage_summary())
    elif args.command == "check":
        semantics = _semantic_dict(args.semantic)
        check = orch.check_required_inputs(args.stage, set(semantics.keys()))
        _print({
            "stage_id": check.stage_id,
            "ready": check.ready,
            "missing_files": check.missing_files,
            "missing_semantic_inputs": check.missing_semantic_inputs,
            "entry_condition_failures": check.entry_condition_failures,
        })
    elif args.command == "packet":
        path = runner.create_execution_packet(
            args.stage, semantic_inputs=_semantic_dict(args.semantic)
        )
        _print({"packet": str(path)})
    elif args.command == "run":
        if args.codex:
            executor = CodexExecReasoningExecutor(
                executable=args.codex_bin,
                model=args.model,
                repo_root=repo,
                telemetry_recorder=telemetry_recorder,
            )
        elif args.openai:
            executor = OpenAIResponsesExecutor(
                model=args.model or "gpt-5.6",
                telemetry_recorder=telemetry_recorder,
            )
        else:
            executor = ExternalCommandExecutor(args.executor_command)
        _print(runner.run(
            executor,
            args.stage,
            semantic_inputs=_semantic_dict(args.semantic),
        ))
    elif args.command == "pipeline":
        if args.provider == "command":
            if not args.executor_command:
                raise SystemExit("--executor-command is required for --provider command")
            executor = ExternalCommandExecutor(args.executor_command)
        elif args.provider == "openai":
            executor = OpenAIResponsesExecutor(
                model=args.model or "gpt-5.6",
                telemetry_recorder=telemetry_recorder,
            )
        else:
            executor = CodexExecReasoningExecutor(
                executable=args.codex_bin,
                model=args.model,
                repo_root=repo,
                telemetry_recorder=telemetry_recorder,
            )
        controller = PipelineController(
            orch, telemetry_recorder=telemetry_recorder
        )
        _print(controller.run_until(
            executor,
            stop_before=args.stop_before,
            max_stages=args.max_stages,
            semantic_by_stage=_semantic_by_stage(args.semantic),
        ))
    elif args.command == "record-result":
        _print(orch.record_stage_result(
            args.stage, args.result, classification=args.classification
        ))
    elif args.command == "route-conflict":
        _print(orch.route_conflict(args.domains))


if __name__ == "__main__":
    try:
        main()
    except (SDDOrchestratorError, ReasoningProviderError, GitRuntimeError, CodexAdapterError, DecisionGatewayError) as exc:
        raise SystemExit(f"SDD error: {exc}")
