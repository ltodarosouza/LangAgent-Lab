"""Travas do agente: settings do Claude Code e hook PreToolUse.

Só valem na sessão aberta por `tools/agente.sh`; sessões humanas nesta pasta
continuam livres. Três camadas, porque uma regra escrita sozinha não basta:

1. **Permissões** (`permissions.deny`): Edit/Write negados em tudo que define a
   busca (código, configs, testes, pesos, dados, regras) e no avaliador; Read
   negado nos documentos do avaliador que contam resultados.
2. **Sandbox** (vale para o Bash e tudo o que ele chama, inclusive Python
   escrito pelo agente): as mesmas negações viram `denyWrite`/`denyRead`, rede
   só para arXiv e PyPI, e nenhum comando roda fora do sandbox.
3. **Hook** (`hook`, roda fora do sandbox a cada ferramenta):
   - escrita só em `workspace/candidate.json` e `runs/`;
   - nada de ler o avaliador pelas ferramentas Read/Grep/Glob;
   - Python só pelos comandos aprovados, e o lote real só passa pelo
     orçamento: no máximo `--max` configurações distintas, e o lote de 37
     casos só depois de um rápido que disse "melhor". O livro-caixa fica em
     `.agente/orcamento.jsonl`, que o agente não consegue escrever.

Uso:
    python3 tools/trava_agente.py settings --max 10 > .agente/settings.json
    python3 tools/trava_agente.py hook --max 10 < entrada_do_claude.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[1]
EVALUATOR = Path(os.environ.get("TEXTURE_EVALUATOR_REPO", ROOT.parent / "synthetic-lung-ct-evaluation")).resolve()
DEFAULT_MAX = 10

# o que o agente pode escrever; todo o resto é negado pelo hook
WRITABLE_FILES = ("workspace/candidate.json",)
WRITABLE_DIRS = ("runs",)
# negados também nas permissões e no sandbox (Bash, Python), para não depender só do hook
PROTECTED = (
    "agent", "generator", "configs", "tests", "tools", "models", "data",
    ".agente", ".claude", ".cursor", ".git",
    "AGENTS.md", "AGENT_PROMPT.md", "README.md", ".gitignore", ".gitattributes",
)
# documentos do avaliador que contam conclusões; o código dele precisa continuar legível para o Python
EVALUATOR_DOCS = ("README.md", "docs", "research", "resultados", "archive", "frameworks/texture_evaluator/README.md")
ALLOWED_DOMAINS = ("arxiv.org", "export.arxiv.org", "pypi.org", "files.pythonhosted.org")
DENIED_BASH = (
    "rm -rf *", "sudo *", "git push *", "git branch -D *", "git reset --hard *", "git clean *",
)

INTERPRETER = re.compile(r"\b(python[\d.]*|ipython|torchrun|pip[\d.]*|uvx?|conda|mamba|accelerate|deepspeed|jupyter)\b")
OTHER_SHELLS = re.compile(r"\b(bash|sh|zsh|eval|exec|source|xargs|env|nohup|perl|ruby|node|osascript)\b")
# um comando aprovado pode ter só `2>&1` e um `| tail/head -n N` no fim
APPROVED_SHAPE = re.compile(r"^(?P<main>[^;&|`$<>\n]+?)(?:\s+2>&1)?(?:\s*\|\s*(?:tail|head)(?:\s+-n)?\s+-?\d+)?\s*$")
PYTHONS = {".venv/bin/python", "./.venv/bin/python", "python", "python3"}


class Guard:
    def __init__(self, root: Path = ROOT, evaluator: Path = EVALUATOR, max_configurations: int = DEFAULT_MAX):
        self.root = root.resolve()
        self.evaluator = evaluator.resolve()
        self.max = max_configurations
        self.ledger = self.root / ".agente" / "orcamento.jsonl"

    # ------------------------------------------------------------ caminhos

    def resolve(self, path: str, cwd: Optional[str] = None) -> Path:
        candidate = Path(path).expanduser()
        if not candidate.is_absolute():
            candidate = Path(cwd or self.root) / candidate
        return candidate.resolve()

    def writable(self, path: Path) -> bool:
        if any(path == self.root / name for name in WRITABLE_FILES):
            return True
        return any(path.is_relative_to(self.root / name) and path != self.root / name for name in WRITABLE_DIRS)

    def touches_evaluator(self, path: Path) -> bool:
        return path == self.evaluator or path.is_relative_to(self.evaluator) or self.evaluator.is_relative_to(path)

    # ------------------------------------------------------------ decisões

    def check(self, tool: str, tool_input: dict, cwd: Optional[str] = None) -> Optional[str]:
        """Motivo da recusa, ou None se a chamada pode seguir para as permissões normais."""
        if tool in {"Edit", "Write", "MultiEdit", "NotebookEdit"}:
            path = tool_input.get("file_path") or tool_input.get("notebook_path") or ""
            if not self.writable(self.resolve(path, cwd)):
                return "o agente só escreve em workspace/candidate.json e em runs/"
            return None
        if tool in {"Read", "Grep", "Glob"}:
            text = json.dumps(tool_input, ensure_ascii=False)
            paths = [tool_input.get(key) for key in ("file_path", "path") if tool_input.get(key)]
            if self.evaluator.name in text or any(self.touches_evaluator(self.resolve(p, cwd)) for p in paths):
                return "o avaliador é uma caixa-preta para o agente: leia os relatórios em runs/"
            return None
        if tool == "Bash":
            return self.check_bash(tool_input.get("command", ""), cwd)
        return None

    def check_bash(self, command: str, cwd: Optional[str]) -> Optional[str]:
        if self.evaluator.name in command:
            return "o avaliador é uma caixa-preta para o agente: leia os relatórios em runs/"
        for segment in re.split(r"[;&|\n()]+", command):
            words = segment.split()
            if words and re.match(r"^(\./)?(runs|workspace)/|^/(private/)?tmp/|^\.$", words[0]):
                return "não execute arquivos de runs/, workspace/ ou /tmp"
        if OTHER_SHELLS.search(command):
            return "não chame outro shell ou interpretador; rode os comandos aprovados diretamente"
        if not INTERPRETER.search(command):
            return None
        shape = APPROVED_SHAPE.match(command.strip())
        if not shape:
            return "rode o comando Python sozinho, sem ;, &&, redirecionamentos ou substituições"
        try:
            argv = shlex.split(shape.group("main"))
        except ValueError:
            return "comando Python mal formado"
        if len(argv) >= 2 and argv[0] in PYTHONS and argv[1] == "generator/run_batch.py":
            return self.check_budget(argv[2:], cwd)
        if argv[:3] in ([p, "-m", "agent.run_experiment"] for p in PYTHONS) and "mock" in argv:
            return None
        if argv[:3] in ([p, "-m", "unittest"] for p in PYTHONS):
            return None
        return ("Python só pelos comandos aprovados: .venv/bin/python generator/run_batch.py ..., "
                "python -m agent.run_experiment --backend mock ... e python -m unittest ...; para ler JSON use jq")

    # ------------------------------------------------------------ orçamento

    def entries(self) -> list:
        if not self.ledger.exists():
            return []
        return [json.loads(line) for line in self.ledger.read_text(encoding="utf-8").splitlines() if line.strip()]

    def check_budget(self, args: list, cwd: Optional[str]) -> Optional[str]:
        parser = argparse.ArgumentParser(add_help=False, exit_on_error=False)
        parser.add_argument("--scope", choices=("quick", "full"), required=True)
        parser.add_argument("--config", default="workspace/candidate.json")
        parser.add_argument("--output-dir", required=True)
        parser.add_argument("--reuse-report")
        parser.add_argument("--compare-to")
        parser.add_argument("--device")
        try:
            parsed, unknown = parser.parse_known_args(args)
        except (argparse.ArgumentError, SystemExit):
            return "run_batch precisa de --scope e --output-dir dentro de runs/real/"
        if unknown:
            return f"argumentos não reconhecidos: {' '.join(unknown)}"
        output_dir = self.resolve(parsed.output_dir, cwd)
        if not output_dir.is_relative_to(self.root / "runs" / "real") or output_dir == self.root / "runs" / "real":
            return "--output-dir precisa ser uma pasta nova dentro de runs/real/"
        config = self.resolve(parsed.config, cwd)
        if not config.is_relative_to(self.root) or not config.is_file():
            return f"configuração não encontrada dentro do laboratório: {parsed.config}"
        candidate = json.loads(config.read_text(encoding="utf-8"))
        key = json.dumps(candidate, sort_keys=True)

        entries = self.entries()
        used = {entry["candidate_key"] for entry in entries}
        if key not in used and len(used) >= self.max:
            return f"orçamento esgotado: {len(used)} de {self.max} configurações já testadas; pare e reporte"

        if parsed.scope == "full":
            if not parsed.reuse_report:
                return "o lote de 37 casos só roda com --reuse-report apontando para o rápido desta configuração"
            report_path = self.resolve(parsed.reuse_report, cwd)
            if not report_path.is_file():
                return f"relatório rápido não encontrado: {parsed.reuse_report}"
            report = json.loads(report_path.read_text(encoding="utf-8"))
            if report.get("scope") != "quick" or report.get("candidate") != candidate or not report.get("completed"):
                return "--reuse-report precisa ser o lote rápido completo desta mesma configuração"
            comparison = report.get("comparison")
            earlier_full = {entry["candidate_key"] for entry in entries if entry["scope"] == "full"}
            if comparison is None:
                if earlier_full - {key}:
                    return "só o baseline sobe para 37 casos sem comparação; compare o rápido com o melhor rápido"
            elif comparison.get("verdict") != "melhor":
                return f"o lote rápido disse '{comparison.get('verdict')}'; só 'melhor' sobe para 37 casos"

        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        with self.ledger.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "time": datetime.now().isoformat(timespec="seconds"),
                "scope": parsed.scope,
                "output_dir": str(output_dir.relative_to(self.root)),
                "candidate": candidate,
                "candidate_key": key,
                "new_configuration": key not in used,
            }, ensure_ascii=False) + "\n")
        return None

    # ------------------------------------------------------------ settings

    def settings(self) -> dict:
        protected = [self.root / name for name in PROTECTED]
        docs = [self.evaluator / name for name in EVALUATOR_DOCS]

        def rule(tool: str, path: Path) -> list:
            # "//" = caminho absoluto nas regras de permissão
            return [f"{tool}(/{path})", f"{tool}(/{path}/**)"]

        hook = f"python3 {shlex.quote(str(self.root / 'tools' / 'trava_agente.py'))} hook --max {self.max}"
        return {
            "permissions": {
                "deny": [
                    *[r for path in [*protected, self.evaluator] for r in rule("Edit", path)],
                    *[r for path in docs for r in rule("Read", path)],
                    *[f"Bash({pattern})" for pattern in DENIED_BASH],
                ],
            },
            "sandbox": {
                "enabled": True,
                "failIfUnavailable": True,
                "autoAllowBashIfSandboxed": True,
                "allowUnsandboxedCommands": False,
                "network": {"allowedDomains": list(ALLOWED_DOMAINS)},
                "filesystem": {
                    "denyWrite": [str(path) for path in [*protected, self.evaluator]],
                    "denyRead": [str(path) for path in docs],
                },
            },
            "env": {
                "MPLCONFIGDIR": str(self.root / "runs" / ".mplconfig"),
                "PYTHONDONTWRITEBYTECODE": "1",
            },
            "hooks": {
                "PreToolUse": [{
                    "matcher": "Bash|Edit|Write|MultiEdit|NotebookEdit|Read|Grep|Glob",
                    "hooks": [{"type": "command", "command": hook, "timeout": 30, "onFailure": "block"}],
                }],
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("mode", choices=("settings", "hook"))
    parser.add_argument("--max", type=int, default=DEFAULT_MAX, help="MAX_CONFIGURATIONS da busca")
    args = parser.parse_args()
    guard = Guard(max_configurations=args.max)
    if args.mode == "settings":
        print(json.dumps(guard.settings(), indent=2, ensure_ascii=False))
        return
    event = json.load(sys.stdin)
    reason = guard.check(event.get("tool_name", ""), event.get("tool_input") or {}, event.get("cwd"))
    if reason:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": f"Trava do laboratório: {reason}.",
        }}, ensure_ascii=False))


if __name__ == "__main__":
    main()
