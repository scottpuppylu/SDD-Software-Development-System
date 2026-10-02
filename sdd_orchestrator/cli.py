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
from .system_controller import (
    GOVERNED_OPERATIONS,
    ChannelNeutralOperationPort,
    FullSystemController,
    GovernedOperationRequest,
    LocalMVPAdapter,
)
from .telemetry.recorder import TelemetryRecorder
from .context_activation import resolve_context_compilation_mode
from .developer_entry import (
    DeveloperEntryError,
    bootstrap_global_config,
    detect_binding,
    enable_repo,
    rebind_repo,
    start_message,
    unbind_repo,
)


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
    sub.add_parser("reconcile-stage07-provenance")

    p_operation = sub.add_parser("operation")
    p_operation.add_argument("--journey", required=True)
    p_operation.add_argument("--command-id", required=True)
    p_operation.add_argument("--operation", required=True, choices=sorted(GOVERNED_OPERATIONS))
    p_operation.add_argument("--target", required=True)
    p_operation.add_argument("--expected-snapshot")
    p_operation.add_argument("--payload-json", default="{}")

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

    p_bootstrap = sub.add_parser("bootstrap", help="Register the user-level SDD runtime")
    p_bootstrap.add_argument("--config")
    p_bootstrap.add_argument("--runtime-path")
    for name, handler in (("enable", enable_repo), ("rebind", rebind_repo), ("unbind", unbind_repo)):
        p_entry = sub.add_parser(name, help=f"{name} SDD binding for a repository")
        p_entry.add_argument("--repo", required=True)
        p_entry.add_argument("--config")
        if name == "enable":
            p_entry.add_argument("--init-git", action="store_true")
    p_detect = sub.add_parser("binding", help="Detect the current SDD project binding")
    p_detect.add_argument("--repo", default=".")
    p_detect.add_argument("--config")

    args = parser.parse_args()
    if args.command == "bootstrap":
        path = bootstrap_global_config(args.config, args.runtime_path)
        _print({"bootstrap": "PASS", "config_path": str(path), "message": start_message()})
        return
    if args.command in {"enable", "rebind", "unbind"}:
        try:
            if args.command == "enable":
                result = enable_repo(args.repo, config_path=args.config, initialize_git=args.init_git)
            elif args.command == "rebind":
                result = rebind_repo(args.repo, config_path=args.config)
            else:
                result = unbind_repo(args.repo, config_path=args.config)
        except DeveloperEntryError as exc:
            raise SystemExit(f"SDD error: {exc}") from exc
        _print(result)
        return
    if args.command == "binding":
        try:
            _print(detect_binding(args.repo, config_path=args.config))
        except DeveloperEntryError as exc:
            raise SystemExit(f"SDD error: {exc}") from exc
        return
    repo = Path(args.repo)
    compilation_mode = resolve_context_compilation_mode()

    if args.command == "operation":
        try:
            payload = json.loads(args.payload_json)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"SDD error: operation payload is not valid JSON: {exc}") from exc
        if not isinstance(payload, dict):
            raise SystemExit("SDD error: operation payload must be a JSON object")
        request = GovernedOperationRequest(
            journey_identity=args.journey,
            command_identity=args.command_id,
            operation=args.operation,
            target_identity=args.target,
            payload=payload,
            expected_snapshot_identity=args.expected_snapshot,
        )
        _print(LocalMVPAdapter(ChannelNeutralOperationPort(Orchestrator(repo))).invoke(request))
        return

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
            codex=CodexCLI(
                executable=args.codex_bin,
                telemetry_recorder=telemetry_recorder,
            ),
            project_python=args.project_python,
            heartbeat_seconds=args.heartbeat_seconds,
            telemetry_recorder=telemetry_recorder,
        )
        controller = FullSystemController(
            orch,
            reasoning,
            codex_runner,
            telemetry_recorder=telemetry_recorder,
            compilation_mode=compilation_mode,
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
        telemetry_recorder = TelemetryRecorder.from_environment(repo)
        codex = CodexCLI(
            executable=args.codex_bin,
            timeout_seconds=args.timeout,
            telemetry_recorder=telemetry_recorder,
        )
        stage08 = Stage08CodexRunner(
            orch,
            codex=codex,
            project_python=args.project_python,
            heartbeat_seconds=args.heartbeat_seconds,
            telemetry_recorder=telemetry_recorder,
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
    if args.command == "reconcile-stage07-provenance":
        _print(orch.reconcile_current_stage08_authorization_provenance(
            preparing_stage07_rerun=True
        ))
        return
    telemetry_recorder = TelemetryRecorder.from_environment(repo)
    runner = StageRunner(
        orch,
        telemetry_recorder=telemetry_recorder,
        compilation_mode=compilation_mode,
    )

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
            orch,
            telemetry_recorder=telemetry_recorder,
            compilation_mode=compilation_mode,
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
    except (SDDOrchestratorError, ReasoningProviderError, GitRuntimeError, CodexAdapterError, DecisionGatewayError, DeveloperEntryError) as exc:
        raise SystemExit(f"SDD error: {exc}")
