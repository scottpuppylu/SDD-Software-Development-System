from __future__ import annotations

from dataclasses import dataclass
import re

@dataclass
class AtomicTask:
    task_id: str
    title: str
    status: str
    raw_markdown: str
    traceability: list[str]
    allowed_paths: list[str]
    verification_commands: list[str]


class TaskFileParser:
    """Parse the minimal Atomic Task contract from tasks.md.

    This parser intentionally rejects vague task scope. Stage 08 must know an
    explicit write boundary before a coding agent is allowed to edit files.
    """

    HEADING = re.compile(
        r"^(#{2,6})\s+((?:T|TASK-?|TC)\d{1,5})\s*(?:[—–:\-]\s*)?(.*)$",
        re.IGNORECASE | re.MULTILINE,
    )

    def __init__(self, text: str):
        self.text = text

    def parse(self) -> list[AtomicTask]:
        matches = list(self.HEADING.finditer(self.text))
        tasks: list[AtomicTask] = []
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(self.text)
            block = self.text[start:end].strip()
            task_id = self._normalize_task_id(match.group(2))
            title = match.group(3).strip() or task_id
            status = self._field(block, "Status") or "TODO"
            trace = self._extract_traceability(block)
            paths = self._extract_allowed_paths(block)
            commands = self._extract_verification_commands(block)
            tasks.append(
                AtomicTask(
                    task_id=task_id,
                    title=title,
                    status=status.upper().strip("[] "),
                    raw_markdown=block,
                    traceability=trace,
                    allowed_paths=paths,
                    verification_commands=commands,
                )
            )
        return tasks

    @staticmethod
    def _normalize_task_id(raw: str) -> str:
        raw = raw.upper().replace("TASK-", "T").replace("TASK", "T")
        if raw.startswith("TC"):
            return raw
        if raw.startswith("T"):
            digits = re.sub(r"\D", "", raw)
            return f"T{int(digits):03d}" if digits else raw
        return raw

    @staticmethod
    def _field(block: str, name: str) -> str | None:
        patterns = [
            rf"^[ \t]*[-*][ \t]*\*\*{re.escape(name)}\*\*[ \t]*:[ \t]*(.+)$",
            rf"^[ \t]*[-*][ \t]*\*\*{re.escape(name)}:\*\*[ \t]*(.+)$",
            rf"^[ \t]*{re.escape(name)}[ \t]*:[ \t]*(.+)$",
        ]
        for pattern in patterns:
            m = re.search(pattern, block, re.IGNORECASE | re.MULTILINE)
            if m:
                return m.group(1).strip()
        return None

    def _extract_traceability(self, block: str) -> list[str]:
        raw = self._field(block, "Traceability") or self._field(block, "Trace") or ""
        ids = re.findall(r"\b(?:G|FR|NFR|EC|AC|SPEC|DES|T|TC)-?[A-Za-z0-9_.]+\b", raw, re.IGNORECASE)
        return list(dict.fromkeys(ids))

    ALLOWED_PATH_FIELDS = (
        "Allowed Paths",
        "Allowed files",
        "Allowed Files",
        "Allowed production files",
        "Allowed Production Files",
        "Allowed test files",
        "Allowed Test Files",
        "Allowed evidence files",
        "Allowed Evidence Files",
        "Write Scope",
    )

    VERIFICATION_COMMAND_FIELDS = (
        "Verification Commands",
        "Verification Command",
    )

    def _extract_allowed_paths(self, block: str) -> list[str]:
        # Stage 08 write scope must come from explicit machine-readable path
        # fields. Implementation Scope is prose describing WHAT to implement;
        # it is intentionally not treated as path authority.
        out: list[str] = []
        for field in self.ALLOWED_PATH_FIELDS:
            raw = self._field(block, field)
            if raw:
                for path in self._paths_from_text(raw):
                    if path not in out:
                        out.append(path)

            section = self._section(block, (field,))
            for path in self._paths_from_text(section):
                if path not in out:
                    out.append(path)
        return out

    def _extract_verification_commands(self, block: str) -> list[str]:
        # Prefer the explicit Stage 06 -> Stage 08 machine contract.
        candidates: list[str] = []
        field_names = self.VERIFICATION_COMMAND_FIELDS
        for name in field_names:
            raw = self._field(block, name)
            if raw:
                candidates.extend(re.findall(r"`([^`]+)`", raw))
                if not re.findall(r"`([^`]+)`", raw) and self._looks_like_command(raw):
                    candidates.append(raw)

            section = self._section(block, (name,))
            candidates.extend(re.findall(r"`([^`]+)`", section))
            for line in section.splitlines():
                # Accept normal Markdown bullets and ordered lists. Stage 06 is
                # free to render Verification Commands as `- cmd` or `1. cmd`;
                # both are the same machine contract.
                stripped = re.sub(r"^\s*(?:[-*]|\d+[.)])\s*", "", line).strip()
                if self._looks_like_command(stripped):
                    candidates.append(stripped.strip("`"))

        cleaned: list[str] = []
        for c in candidates:
            c = c.strip()
            if c and self._looks_like_command(c) and c not in cleaned:
                cleaned.append(c)
        return cleaned

    @staticmethod
    def _section(block: str, names: tuple[str, ...]) -> str:
        alt = "|".join(re.escape(n) for n in names)
        patterns = [
            rf"^#{2,6}\s+(?:{alt})\s*$",
            rf"^[ \t]*[-*][ \t]*\*\*(?:{alt})\*\*[ \t]*:[ \t]*$",
            rf"^[ \t]*[-*][ \t]*\*\*(?:{alt}):\*\*[ \t]*$",
        ]
        for pattern in patterns:
            m = re.search(pattern, block, re.IGNORECASE | re.MULTILINE)
            if not m:
                continue
            rest = block[m.end():]
            stop = re.search(r"^#{2,6}\s+|^\s*[-*]\s*\*\*[A-Za-z][^*]+\*\*\s*:", rest, re.MULTILINE)
            return rest[:stop.start()] if stop else rest
        return ""

    @staticmethod
    def _paths_from_text(text: str) -> list[str]:
        candidates = re.findall(r"`([^`]+)`", text)
        candidates += re.findall(
            r"(?<![\w.-])((?:src|tests|test|app|lib|packages|scripts|public|config|docs)/[^\s,;]+|(?:pyproject\.toml|package\.json|requirements[^\s,;]*\.txt))",
            text,
        )
        out: list[str] = []
        for value in candidates:
            # Preserve meaningful leading dots (for example `.sdd/...`) while
            # removing Markdown delimiters and trailing sentence punctuation.
            value = value.strip().strip("` \t\r\n").rstrip("`.,:;()[]{}。；，： \t\r\n")
            if TaskFileParser._looks_like_path(value) and value not in out:
                out.append(value)
        return out

    @staticmethod
    def _looks_like_path(value: str) -> bool:
        if any(op in value for op in ("&&", "||", ">", "<", "|")):
            return False
        return "/" in value or value in {"pyproject.toml", "package.json"} or value.endswith((".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yaml", ".yml"))

    @staticmethod
    def _looks_like_command(value: str) -> bool:
        value = value.strip().strip("`")
        if re.match(r"^\.\\\.venv\\Scripts\\python\.exe\s+-m\s+pytest\s+\S+", value):
            return True
        if re.match(r"^(?:python(?:3)?\s+-m\s+pytest|pytest|npm\s+(?:test|run\s+\S+)|pnpm\s+(?:test|run\s+\S+)|yarn\s+(?:test|\S+)|ruff\s+check|mypy|go\s+test|cargo\s+test|dotnet\s+test)\b", value):
            return True
        if re.fullmatch(r"python(?:3)?\s+-m\s+pip\s+install\s+-e\s+\.", value):
            return True
        if re.fullmatch(r"python(?:3)?\s+-c\s+[\"']import\s+[A-Za-z_][A-Za-z0-9_.]*[\"']", value):
            return True
        if re.fullmatch(r"python(?:3)?\s+-m\s+[A-Za-z_][A-Za-z0-9_.]*\s+--help", value):
            return True
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.-]*\s+--help", value):
            return True
        if re.fullmatch(r"git\s+status\s+--short", value):
            return True
        if re.fullmatch(r"git\s+diff\s+--check", value):
            return True
        if re.fullmatch(r"git\s+log\s+--oneline\s+--decorate\s+-\d+", value):
            return True
        return False


