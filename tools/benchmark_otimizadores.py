"""Benchmark de otimizadores clássicos no backend mock.

Pergunta: com o mesmo orçamento de avaliações, um otimizador determinístico ou
clássico encontra parâmetros tão bons quanto o agente LLM?

Só usa o backend mock (`agent.mock_backend.run_mock` + `agent.score.score_cases`),
as mesmas funções de `python -m agent.run_experiment --backend mock`. Não grava em
`runs/history.jsonl`, para não misturar com a trajetória do agente; os resultados vão
para `runs/benchmark-otimizadores/<data>/`.

Regras de justiça:
- todos os métodos começam avaliando `configs/baseline.json` (como o agente);
- o orçamento conta configurações distintas; repetir uma configuração já medida é
  reaproveitamento e não gasta orçamento (como manda o AGENTS.md);
- o espaço é o `configs/search_space.json` inteiro; o otimizador não sabe quais
  dimensões o mock ignora;
- `scale_factor` e `seed` ficam congelados (só têm uma opção no espaço).

Uso:
    python tools/benchmark_otimizadores.py --budget 20 --repeats 30
    python tools/benchmark_otimizadores.py --agent-history ../../../runs/history.jsonl

Dependências opcionais: scipy (Nelder-Mead), optuna (TPE), cma (CMA-ES), matplotlib
(gráfico). Um método cuja dependência falta é pulado com aviso.
"""

from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
import random
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.config import load_json, validate_candidate  # noqa: E402
from agent.mock_backend import run_mock  # noqa: E402
from agent.score import score_cases  # noqa: E402


class BudgetExhausted(Exception):
    pass


class Space:
    """Codifica o espaço de busca num cubo unitário [0, 1]^d.

    Dimensões com várias opções viram um intervalo dividido em faixas iguais (uma por
    opção, na ordem do JSON); dimensões contínuas são escaladas linearmente; dimensões
    com uma única opção ficam congeladas e não entram no cubo.
    """

    def __init__(self, search_space: dict, baseline: dict, only: list | None = None):
        self.rules = search_space
        self.free = []
        self.frozen = {}
        for name, rule in search_space.items():
            choices = rule.get("choices")
            if choices is not None and len(choices) == 1:
                self.frozen[name] = choices[0]
            elif only and name not in only:
                self.frozen[name] = baseline[name]
            else:
                self.free.append(name)

    @property
    def dim(self) -> int:
        return len(self.free)

    def decode(self, u) -> dict:
        candidate = dict(self.frozen)
        for name, value in zip(self.free, u):
            value = min(max(float(value), 0.0), 1.0)
            rule = self.rules[name]
            if "choices" in rule:
                choices = rule["choices"]
                candidate[name] = choices[min(int(value * len(choices)), len(choices) - 1)]
            else:
                raw = rule["min"] + value * (rule["max"] - rule["min"])
                candidate[name] = int(round(raw)) if rule["type"] == "integer" else round(raw, 4)
        return {name: candidate[name] for name in self.rules}

    def encode(self, candidate: dict) -> list:
        u = []
        for name in self.free:
            rule = self.rules[name]
            if "choices" in rule:
                choices = rule["choices"]
                u.append((choices.index(candidate[name]) + 0.5) / len(choices))
            else:
                u.append((candidate[name] - rule["min"]) / (rule["max"] - rule["min"]))
        return u

    def random_point(self, rng: random.Random) -> list:
        return [rng.random() for _ in self.free]


def key_of(candidate: dict) -> str:
    return json.dumps(candidate, sort_keys=True)


def evaluate_once(candidate: dict) -> dict:
    candidate = validate_candidate(candidate)
    cases = run_mock(candidate)
    summary = score_cases(cases)
    verdicts = [case["verdicts"] for case in cases]
    return {
        "candidate": candidate,
        "score": summary["score"],
        "valid": summary["valid"],
        "invalid_cases": summary["invalid_cases"],
        "approved_cases": summary["approved_cases"],
        "brightness_violations": sum(v["brightness"] != "aprovada" for v in verdicts),
        "pair_violations": sum(v["pair_status"] != "ok" for v in verdicts),
        "texture_violations": sum(v["texture"] != "aprovada" for v in verdicts),
    }


class Evaluator:
    """Conta configurações distintas e guarda a trajetória na ordem de avaliação."""

    def __init__(self, budget: int, max_calls: int):
        self.budget = budget
        self.max_calls = max_calls
        self.calls = 0
        self.cache = {}
        self.trajectory = []

    def __call__(self, candidate: dict) -> float:
        self.calls += 1
        key = key_of(candidate)
        if key in self.cache:
            return self.cache[key]["score"]
        if len(self.trajectory) >= self.budget or self.calls > self.max_calls:
            raise BudgetExhausted
        result = evaluate_once(candidate)
        self.cache[key] = result
        self.trajectory.append(result)
        return result["score"]

    @property
    def done(self) -> bool:
        return len(self.trajectory) >= self.budget or self.calls >= self.max_calls


# --- métodos -----------------------------------------------------------------


def method_random(space, ev, baseline, rng):
    ev(baseline)
    while not ev.done:
        ev(space.decode(space.random_point(rng)))


def method_coordinate(space, ev, baseline, rng):
    """Pattern search (busca por compasso) determinística a partir do baseline.

    Testa +passo e -passo em cada coordenada, na ordem do JSON, e anda para a primeira
    melhora (oportunista). Se nenhuma direção melhora, divide o passo por dois.
    """
    x = space.encode(baseline)
    fx = ev(baseline)
    step = INITIAL_STEP["coordenada"]
    while not ev.done and step > 1e-3:
        improved = False
        for i in range(space.dim):
            for sign in (1.0, -1.0):
                y = list(x)
                y[i] = min(max(y[i] + sign * step, 0.0), 1.0)
                fy = ev(space.decode(y))
                if fy > fx:
                    x, fx, improved = y, fy, True
                    break
            if improved:
                break
        if not improved:
            step /= 2.0


def method_nelder_mead(space, ev, baseline, rng):
    from scipy.optimize import minimize

    x0 = space.encode(baseline)
    simplex = [x0]
    for i in range(space.dim):
        y = list(x0)
        delta = INITIAL_STEP["nelder_mead"]
        y[i] = y[i] + delta if y[i] + delta <= 1.0 else y[i] - delta
        simplex.append(y)
    try:
        minimize(
            lambda u: -ev(space.decode(u)),
            x0,
            method="Nelder-Mead",
            options={"initial_simplex": simplex, "maxfev": ev.max_calls, "xatol": 1e-4, "fatol": 1e-6},
        )
    except BudgetExhausted:
        pass


def method_tpe(space, ev, baseline, rng):
    import optuna

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    sampler = optuna.samplers.TPESampler(seed=rng.randrange(2**31), n_startup_trials=5)
    study = optuna.create_study(direction="maximize", sampler=sampler)
    study.enqueue_trial({name: baseline[name] for name in space.free})

    def objective(trial):
        candidate = dict(space.frozen)
        for name in space.free:
            rule = space.rules[name]
            if "choices" in rule:
                candidate[name] = trial.suggest_categorical(name, rule["choices"])
            elif rule["type"] == "integer":
                candidate[name] = trial.suggest_int(name, rule["min"], rule["max"])
            else:
                candidate[name] = trial.suggest_float(name, rule["min"], rule["max"])
        return ev({name: candidate[name] for name in space.rules})

    while not ev.done:
        try:
            study.optimize(objective, n_trials=1)
        except BudgetExhausted:
            break


def method_gp_bo(space, ev, baseline, rng):
    """GP-BO simples em numpy: kernel RBF (comprimento 0,3), Expected Improvement
    maximizado sobre 2000 pontos aleatórios do cubo. Começa com baseline + 4 aleatórios."""
    import numpy as np

    np_rng = np.random.default_rng(rng.randrange(2**31))
    X, y = [], []

    def observe(u):
        candidate = space.decode(u)
        y.append(ev(candidate))
        X.append(space.encode(candidate))  # posição canônica da configuração decodificada

    observe(space.encode(baseline))
    for _ in range(4):
        if ev.done:
            return
        observe(space.random_point(rng))

    length, noise = 0.3, 1e-3
    # numpy 2 com o BLAS do macOS emite avisos espúrios de overflow em matmul; o
    # resultado é conferido com isfinite logo abaixo.
    np.seterr(all="ignore")
    while not ev.done:
        Xa, ya = np.array(X), np.array(y)
        mu_y, sd_y = ya.mean(), ya.std() or 1.0
        yn = (ya - mu_y) / sd_y

        def kernel(A, B):
            d2 = ((A[:, None, :] - B[None, :, :]) ** 2).sum(-1)
            return np.exp(-0.5 * d2 / length**2)

        K = kernel(Xa, Xa) + noise * np.eye(len(Xa))
        L = np.linalg.cholesky(K)
        alpha = np.linalg.solve(L.T, np.linalg.solve(L, yn))
        cand = np_rng.random((2000, space.dim))
        Ks = kernel(cand, Xa)
        mean = Ks @ alpha
        v = np.linalg.solve(L, Ks.T)
        sd = np.sqrt(np.clip(1.0 - (v**2).sum(0), 1e-12, None))
        best = yn.max()
        z = (mean - best) / sd
        cdf = 0.5 * (1 + np.vectorize(math.erf)(z / math.sqrt(2)))
        pdf = np.exp(-0.5 * z**2) / math.sqrt(2 * math.pi)
        ei = (mean - best) * cdf + sd * pdf
        if not np.isfinite(ei).all():
            raise FloatingPointError("EI não finito no GP-BO")
        seen = {key_of(space.decode(x)) for x in X}
        for idx in np.argsort(-ei):
            if key_of(space.decode(cand[idx])) not in seen:
                observe(list(cand[idx]))
                break
        else:
            observe(space.random_point(rng))


def method_cma(space, ev, baseline, rng):
    import cma

    es = cma.CMAEvolutionStrategy(
        space.encode(baseline),
        0.3,
        {"bounds": [0, 1], "seed": rng.randrange(1, 2**31), "verbose": -9},
    )
    ev(baseline)
    try:
        while not ev.done and not es.stop():
            xs = es.ask()
            es.tell(xs, [-ev(space.decode(x)) for x in xs])
    except BudgetExhausted:
        pass


# Passo inicial dos métodos determinísticos, no cubo unitário (sobrescrito por --step).
INITIAL_STEP = {"coordenada": 0.25, "nelder_mead": 0.2}

METHODS = {
    "aleatoria": (method_random, True, None),
    "coordenada": (method_coordinate, False, None),
    "nelder_mead": (method_nelder_mead, False, "scipy"),
    "tpe": (method_tpe, True, "optuna"),
    "gp_bo": (method_gp_bo, True, "numpy"),
    "cma_es": (method_cma, True, "cma"),
}


# --- análise -----------------------------------------------------------------


def best_so_far(trajectory: list, budget: int) -> list:
    """Melhor score válido até a avaliação k. Configuração inválida não conta como melhor."""
    curve, best = [], 0.0
    for result in trajectory:
        if result["valid"]:
            best = max(best, result["score"])
        curve.append(best)
    curve += [best] * (budget - len(curve))  # método que parou antes mantém o melhor
    return curve


def reference_optimum(space: Space, baseline: dict) -> dict:
    """Ótimo da grade das dimensões discretas, com as contínuas no valor do baseline."""
    discrete = [n for n in space.free if "choices" in space.rules[n]]
    best = None
    for values in itertools.product(*(space.rules[n]["choices"] for n in discrete)):
        candidate = dict(baseline, **dict(zip(discrete, values)))
        result = evaluate_once(candidate)
        if result["valid"] and (best is None or result["score"] > best["score"]):
            best = result
    return best


def load_agent_curve(path: Path, budget: int):
    if path is None or not path.exists():
        return None
    trajectory = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        summary = row["summary"]
        trajectory.append({"score": summary["score"], "valid": summary["valid"]})
    return trajectory, best_so_far(trajectory[:budget], budget)


def quantile(values, q):
    values = sorted(values)
    pos = (len(values) - 1) * q
    lo, hi = math.floor(pos), math.ceil(pos)
    return values[lo] + (values[hi] - values[lo]) * (pos - lo)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--budget", type=int, default=20, help="configurações distintas por execução")
    parser.add_argument("--repeats", type=int, default=30, help="repetições dos métodos estocásticos")
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--methods", nargs="*", default=list(METHODS))
    parser.add_argument("--only", nargs="*", default=None,
                        help="restringe a busca a estas dimensões; as demais ficam no valor do baseline")
    parser.add_argument("--step", type=float, default=None,
                        help="passo inicial da coordenada e do simplex do Nelder-Mead (cubo unitário)")
    parser.add_argument("--agent-history", type=Path, default=None,
                        help="history.jsonl de uma busca do agente no mock, para comparar")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    baseline = validate_candidate(load_json(ROOT / "configs" / "baseline.json"))
    space = Space(load_json(ROOT / "configs" / "search_space.json"), baseline, args.only)
    reference = reference_optimum(space, baseline)
    out = args.out or ROOT / "runs" / "benchmark-otimizadores" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    if args.step is not None:
        INITIAL_STEP.update(coordenada=args.step, nelder_mead=args.step)
    max_calls = 50 * args.budget  # evita laço infinito em platôs de configurações repetidas

    runs = {}
    for name in args.methods:
        func, stochastic, dependency = METHODS[name]
        repeats = args.repeats if stochastic else 1
        runs[name] = []
        try:
            for r in range(repeats):
                rng = random.Random(args.seed * 1000 + r)
                ev = Evaluator(args.budget, max_calls)
                try:
                    func(space, ev, baseline, rng)
                except BudgetExhausted:
                    pass
                runs[name].append(ev.trajectory)
        except ImportError as error:
            print(f"[aviso] {name} pulado: falta {dependency} ({error})")
            del runs[name]

    tol = 1e-6
    report = {
        "budget": args.budget,
        "repeats": args.repeats,
        "free_dims": space.free,
        "initial_step": INITIAL_STEP,
        "reference_optimum": reference,
        "baseline_score": evaluate_once(baseline)["score"],
        "methods": {},
    }
    curves_rows = []
    for name, trajectories in runs.items():
        curves = [best_so_far(t, args.budget) for t in trajectories]
        finals = [c[-1] for c in curves]
        hits = [next((k + 1 for k, v in enumerate(c) if v >= reference["score"] - tol), None) for c in curves]
        all_evals = [e for t in trajectories for e in t]
        best_runs = [max((e for e in t if e["valid"]), key=lambda e: e["score"]) for t in trajectories]
        report["methods"][name] = {
            "repeats": len(trajectories),
            "evals_used_mean": statistics.mean(len(t) for t in trajectories),
            "final_best_median": statistics.median(finals),
            "final_best_mean": statistics.mean(finals),
            "final_best_min": min(finals),
            "regret_median": reference["score"] - statistics.median(finals),
            "hit_optimum_rate": sum(h is not None for h in hits) / len(hits),
            "evals_to_optimum_median": statistics.median([h for h in hits if h]) if any(hits) else None,
            "invalid_eval_rate": sum(not e["valid"] for e in all_evals) / len(all_evals),
            "brightness_violations": sum(e["brightness_violations"] for e in all_evals),
            "pair_violations": sum(e["pair_violations"] for e in all_evals),
            "texture_violation_rate": sum(e["texture_violations"] > 0 for e in all_evals) / len(all_evals),
            "best_respects_constraints": all(b["valid"] and b["invalid_cases"] == 0 for b in best_runs),
            "example_best": best_runs[0]["candidate"],
        }
        for k in range(args.budget):
            column = [c[k] for c in curves]
            curves_rows.append({
                "method": name,
                "eval": k + 1,
                "median": statistics.median(column),
                "q25": quantile(column, 0.25),
                "q75": quantile(column, 0.75),
                "min": min(column),
                "hit_rate": sum(v >= reference["score"] - tol for v in column) / len(column),
            })

    agent = load_agent_curve(args.agent_history, args.budget)
    if agent:
        trajectory, curve = agent
        report["agent"] = {"evals": len(trajectory), "final_best": max(curve), "curve": curve[: len(trajectory)]}
        for k, v in enumerate(curve[: len(trajectory)]):
            curves_rows.append({"method": "agente_llm", "eval": k + 1, "median": v, "q25": v, "q75": v,
                                "min": v, "hit_rate": float(v >= reference["score"] - tol)})

    (out / "resultado.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (out / "trajetorias.json").write_text(json.dumps(runs, ensure_ascii=False) + "\n", encoding="utf-8")
    with (out / "curvas.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(curves_rows[0]))
        writer.writeheader()
        writer.writerows(curves_rows)

    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, ax = plt.subplots(figsize=(8, 5))
        for name in list(runs) + (["agente_llm"] if agent else []):
            rows = [r for r in curves_rows if r["method"] == name]
            xs = [r["eval"] for r in rows]
            style = {"color": "black", "linewidth": 2.5, "marker": "o"} if name == "agente_llm" else {}
            ax.plot(xs, [r["median"] for r in rows], label=name, **style)
            if name != "agente_llm" and len(runs[name]) > 1:
                ax.fill_between(xs, [r["q25"] for r in rows], [r["q75"] for r in rows], alpha=0.15)
        ax.axhline(reference["score"], color="gray", linestyle="--", label="ótimo (grade)")
        ax.set_xlabel("avaliações (configurações distintas)")
        ax.set_ylabel("melhor score válido até aqui (mediana, faixa IQR)")
        ax.set_ylim(report["baseline_score"] - 3, reference["score"] + 0.5)
        ax.legend()
        ax.grid(alpha=0.3)
        fig.tight_layout()
        fig.savefig(out / "curvas.png", dpi=120)
    except ImportError:
        print("[aviso] matplotlib ausente: gráfico não gerado")

    print(f"Ótimo de referência: {reference['score']:.4f} em {reference['candidate']}")
    print(f"Baseline: {report['baseline_score']:.4f}")
    header = f"{'método':<12} {'rep':>4} {'mediana':>8} {'pior':>8} {'acerto':>7} {'aval.p/ótimo':>13} {'inválidas':>10}"
    print(header)
    for name, m in report["methods"].items():
        eto = m["evals_to_optimum_median"]
        print(f"{name:<12} {m['repeats']:>4} {m['final_best_median']:>8.4f} {m['final_best_min']:>8.4f} "
              f"{m['hit_optimum_rate']:>7.0%} {eto if eto is not None else '-':>13} {m['invalid_eval_rate']:>10.0%}")
    if agent:
        print(f"{'agente_llm':<12} {1:>4} {report['agent']['final_best']:>8.4f}  ({report['agent']['evals']} avaliações)")
    print(f"Saída: {out}")


if __name__ == "__main__":
    main()
