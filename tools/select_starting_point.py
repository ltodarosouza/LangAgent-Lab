"""Escolhe uma execução completa como ponto de partida da próxima busca.

Uso humano (fora da sessão travada do agente):

    .venv/bin/python tools/select_starting_point.py \
        --from-run runs/real/candidate-01-full

Sem ``--from-run``, apenas mostra o ponto de partida atual.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "runs" / "real"
STATE = ROOT / "workspace" / "search_state.json"
CANDIDATE = ROOT / "workspace" / "candidate.json"
LEDGER = ROOT / ".agente" / "orcamento.jsonl"
DEFAULT_BASELINE_QUICK = RUNS / "baseline-quick" / "report.json"
DEFAULT_BASELINE_FULL = RUNS / "baseline-full" / "report.json"


def load_report(path: Path, scope: str) -> dict:
    path = path.resolve()
    if not path.is_file():
        raise ValueError(f"relatório não encontrado: {path}")
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("scope") != scope:
        raise ValueError(f"{path} não é um relatório {scope}")
    if not report.get("completed"):
        raise ValueError(f"{path} ainda não está completo")
    if not isinstance(report.get("candidate"), dict):
        raise ValueError(f"{path} não contém parâmetros de candidato")
    return report


def report_path(value: Path) -> Path:
    path = value.resolve()
    return path / "report.json" if path.is_dir() else path


def relative(path: Path) -> str:
    resolved = path.resolve()
    if not resolved.is_relative_to(ROOT):
        raise ValueError(f"o relatório precisa estar dentro do laboratório: {resolved}")
    return str(resolved.relative_to(ROOT))


def case_ids(report: dict) -> list[str]:
    return sorted(case["case_id"] for case in report.get("cases", []))


def matching_quick(full_path: Path, candidate: dict) -> Path:
    name = full_path.parent.name
    direct = full_path.parent.with_name(name[:-5] + "-quick") / "report.json" if name.endswith("-full") else None
    candidates = ([direct] if direct else []) + sorted(RUNS.glob("*/report.json"))
    seen: set[Path] = set()
    for path in candidates:
        if path is None or path in seen or not path.is_file():
            continue
        seen.add(path)
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if report.get("scope") == "quick" and report.get("completed") and report.get("candidate") == candidate:
            return path.resolve()
    raise ValueError("não encontrei um lote rápido completo com os mesmos parâmetros")


def archive_ledger() -> Path | None:
    if not LEDGER.exists():
        return None
    history = LEDGER.parent / "historico"
    history.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destination = history / f"orcamento-{stamp}.jsonl"
    suffix = 1
    while destination.exists():
        destination = history / f"orcamento-{stamp}-{suffix}.jsonl"
        suffix += 1
    LEDGER.rename(destination)
    return destination


def select_starting_point(from_run: Path, baseline_quick: Path, baseline_full: Path) -> dict:
    full_path = report_path(from_run)
    full = load_report(full_path, "full")
    quick_path = matching_quick(full_path, full["candidate"])
    quick = load_report(quick_path, "quick")
    baseline_quick_path = report_path(baseline_quick)
    baseline_full_path = report_path(baseline_full)
    baseline_q = load_report(baseline_quick_path, "quick")
    baseline_f = load_report(baseline_full_path, "full")

    if quick["candidate"] != full["candidate"]:
        raise ValueError("os lotes rápido e completo do ponto de partida usam parâmetros diferentes")
    if case_ids(quick) != case_ids(baseline_q):
        raise ValueError("o rápido escolhido não usa os mesmos casos do baseline rápido")
    if case_ids(full) != case_ids(baseline_f):
        raise ValueError("o completo escolhido não usa os mesmos casos do baseline completo")

    state = {
        "schema_version": 1,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "baseline": {
            "quick": relative(baseline_quick_path),
            "full": relative(baseline_full_path),
        },
        "current_best": {
            "quick": relative(quick_path),
            "full": relative(full_path),
            "candidate": full["candidate"],
        },
    }
    archived = archive_ledger()
    CANDIDATE.write_text(json.dumps(full["candidate"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if archived:
        state["archived_ledger"] = relative(archived)
    return state


def show_state() -> dict:
    if not STATE.is_file():
        raise ValueError("nenhum ponto de partida foi escolhido; use --from-run")
    return json.loads(STATE.read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-run", type=Path, help="pasta ou report.json do melhor lote completo")
    parser.add_argument("--baseline-quick", type=Path, default=DEFAULT_BASELINE_QUICK)
    parser.add_argument("--baseline-full", type=Path, default=DEFAULT_BASELINE_FULL)
    args = parser.parse_args()
    state = (select_starting_point(args.from_run, args.baseline_quick, args.baseline_full)
             if args.from_run else show_state())
    print(json.dumps(state, indent=2, ensure_ascii=False))
    print("\nPróximo passo: MAX_CONFIGURATIONS=10 ./tools/agente.sh")


if __name__ == "__main__":
    main()
