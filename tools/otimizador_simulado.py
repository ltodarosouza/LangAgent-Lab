"""Backend simulado para testar `tools/otimizador_real.py` sem GPU.

Escreve relatórios com o mesmo formato de `generator/run_batch.py` (casos, `summary`,
`comparison`), usando as funções verdadeiras de `generator/reporting.py` para resumir e
comparar. As métricas por caso vêm de uma função inventada dos cinco parâmetros, com
interações, ruído por caso e regiões inválidas (rejeições e pares suspeitos).

Não diz nada sobre o LDM real: serve só para exercitar funil, orçamento, restrições,
reaproveitamento de casos e log de ponta a ponta.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT, ROOT / "generator"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from agent.config import load_json  # noqa: E402
from reporting import DISTANCE_METRICS, compare_reports, load_report, summarize  # noqa: E402

# Distância média do baseline por métrica, só para dar escala parecida com a real.
BASE_DISTANCE = {
    "glcm_contrast_z": 1.2,
    "glcm_energy_z": 2.0,
    "wavelet_fine_z": 1.1,
    "wavelet_coarse_z": 1.4,
    "wavelet_entropy_z": 1.3,
    "wavelet_ll_z": 0.6,
    "nex_delta": 0.08,
}
WEIGHT = {
    "glcm_contrast_z": 0.8,
    "glcm_energy_z": 1.3,
    "wavelet_fine_z": 0.7,
    "wavelet_coarse_z": 1.1,
    "wavelet_entropy_z": 1.2,
    "wavelet_ll_z": 0.6,
    "nex_delta": 0.9,
}


def case_lists() -> dict:
    screen = load_json(ROOT / "configs" / "screen_cases.json")["cases"]
    quick = load_json(ROOT / "configs" / "quick_cases.json")["cases"]
    full = quick + [f"sim-caso-{index:02d}" for index in range(27)]
    return {"screen": screen, "quick": quick, "full": full}


def unit_hash(*parts) -> float:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode()).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def quality(candidate: dict) -> float:
    """Fração de melhora 'verdadeira' (inventada). Ótimo interior, com interações."""
    s = float(candidate["steps"])
    n = float(candidate["noise_level"])
    e = float(candidate["eta"])
    lat = float(candidate["latent_noise_scale"])
    cond = float(candidate["conditioning_noise_scale"])
    q_steps = 0.10 * math.exp(-(((s - 40.0) / 18.0) ** 2)) - 0.05
    q_eta = 0.30 * e - 0.25 * e**2
    q_cond = 0.20 * (cond - 1.0) * (0.2 + e) - 0.18 * (cond - 1.0) ** 2
    q_lat = -0.8 * (lat - 1.0) ** 2 - 0.15 * max(0.0, lat - 1.0)
    q_noise = -0.02 * math.log1p(n) + 0.02 * math.log1p(1.0)
    return q_steps + q_eta + q_cond + q_lat + q_noise


def simulate_case(case_id: str, candidate: dict) -> dict:
    key = json.dumps(candidate, sort_keys=True)
    q = quality(candidate)
    lat = float(candidate["latent_noise_scale"])
    noise = float(candidate["noise_level"])
    rejected = lat > 1.08 and unit_hash(case_id, "rej") < (lat - 1.08) / 0.12
    suspect = rejected or (noise > 60 and unit_hash(case_id, "par") < (noise - 60) / 290)
    measurements = {"case_id": case_id}
    for metric in DISTANCE_METRICS:
        case_scale = 0.6 + 0.8 * unit_hash(case_id, metric)
        jitter = 0.04 * (unit_hash(case_id, metric, key) - 0.5)  # "ruído de geração"
        factor = max(0.05, 1.0 - WEIGHT[metric] * q + jitter)
        if rejected:
            factor *= 3.0
        measurements[metric] = BASE_DISTANCE[metric] * case_scale * factor
    measurements.update({
        "glcm_energy_real": 0.04,
        "glcm_energy_synthetic": 0.04 * (1.0 + measurements["glcm_energy_z"] / 3.0),
        "delta_mu": 0.01,
        "wavelet_ll_real": 0.47,
        "wavelet_ll_synthetic": 0.47 - 0.02 * measurements["wavelet_ll_z"],
        "wavelet_fine_pct": 100.0 - 15.0 * measurements["wavelet_fine_z"],
        "wavelet_coarse_pct": 100.0 - 15.0 * measurements["wavelet_coarse_z"],
        "glcm_contrast_pct": 100.0 - 15.0 * measurements["glcm_contrast_z"],
        "wavelet_ratio": 1.0,
        "density_status": "ok",
        "nex_status": "ok",
    })
    return {
        "case_id": case_id,
        "generation": {"simulado": True},
        "evaluation": {
            "verdicts": {
                "final": "rejeitar" if rejected else "revisar",
                "pair_status": "suspeito" if suspect else "ok",
                "brightness": "aprovada",
                "texture": "aprovada",
            },
            "measurements": measurements,
        },
        "previews": {},
    }


def write_report(payload: dict, run_dir: Path) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "report.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_stage(candidate: dict, scope: str, run_dir: Path, reuse_report: Path | None,
              baseline_report: Path | None, compare_to: Path | None) -> dict:
    """Equivalente simulado de uma chamada de `generator/run_batch.py`."""
    reused = {}
    if reuse_report is not None:
        previous = load_report(reuse_report)
        if previous["candidate"] != candidate:
            raise ValueError("o relatório reutilizado foi gerado com outros parâmetros")
        reused = {case["case_id"]: {**case, "reused_from": str(reuse_report)} for case in previous["cases"]}
    cases = [reused.get(case_id) or simulate_case(case_id, candidate) for case_id in case_lists()[scope]]
    payload = {
        "schema_version": 1,
        "run": run_dir.name,
        "scope": scope,
        "completed": True,
        "candidate": candidate,
        "dataset": {"manifest": "simulado", "requested_case_count": len(cases)},
        "summary": summarize(cases),
        "cases": cases,
    }
    if baseline_report is not None:
        baseline = load_report(baseline_report)
        best = load_report(compare_to) if compare_to else None
        payload["comparison"] = {
            "baseline": str(baseline_report),
            "reference": str(compare_to) if compare_to else None,
            **compare_reports(payload, baseline, best),
        }
    write_report(payload, run_dir)
    return payload


def ensure_baselines(out_dir: Path, baseline: dict) -> dict:
    """Cria os três relatórios de baseline simulados (5 ⊂ 10 ⊂ 37), uma vez só."""
    paths = {}
    previous = None
    for scope in ("screen", "quick", "full"):
        run_dir = out_dir / f"baseline-{scope}"
        if not (run_dir / "report.json").exists():
            run_stage(baseline, scope, run_dir, previous, None, None)
        previous = run_dir / "report.json"
        paths[scope] = previous
    return paths
