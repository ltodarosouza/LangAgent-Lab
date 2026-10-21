"""Agregação transparente dos resultados reais do avaliador."""
from __future__ import annotations

import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean, median, pstdev


PERCENT_IDEALS = (
    "wavelet_fine_pct",
    "wavelet_coarse_pct",
    "glcm_contrast_pct",
    "glcm_energy_pct",
)


def enrich_measurements(measurements: dict) -> dict:
    values = dict(measurements)
    real = float(values["glcm_energy_real"])
    synthetic = float(values["glcm_energy_synthetic"])
    values["glcm_energy_pct"] = 100.0 * synthetic / real if real else None
    values["abs_delta_mu"] = abs(float(values["delta_mu"]))
    values["abs_delta_ll"] = abs(float(values["wavelet_ll_synthetic"]) - float(values["wavelet_ll_real"]))
    return values


def case_score(evaluation: dict) -> float:
    values = enrich_measurements(evaluation["measurements"])
    texture_error = mean(min(abs(float(values[key]) - 100.0), 100.0) for key in PERCENT_IDEALS)
    ratio_error = min(abs(float(values["wavelet_ratio"]) - 1.0) * 100.0, 100.0)
    score = 100.0 - 0.75 * texture_error - 0.25 * ratio_error
    verdicts = evaluation["verdicts"]
    if verdicts["pair_status"] != "ok":
        score -= 40.0
    if verdicts["brightness"] != "aprovada":
        score -= 20.0
    if values.get("density_status") != "ok":
        score -= 10.0
    if values.get("nex_status") != "ok":
        score -= 5.0
    return round(max(0.0, min(100.0, score)), 4)


def numeric_statistics(evaluations: list[dict]) -> dict:
    collected: dict[str, list[float]] = {}
    for evaluation in evaluations:
        for key, value in enrich_measurements(evaluation["measurements"]).items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                continue
            number = float(value)
            if math.isfinite(number):
                collected.setdefault(key, []).append(number)
    return {
        key: {
            "mean": round(mean(values), 6),
            "median": round(median(values), 6),
            "std": round(pstdev(values), 6),
            "min": round(min(values), 6),
            "max": round(max(values), 6),
        }
        for key, values in sorted(collected.items())
    }


def summarize(records: list[dict]) -> dict:
    evaluations = [record["evaluation"] for record in records]
    scores = [case_score(evaluation) for evaluation in evaluations]
    verdicts = [evaluation["verdicts"] for evaluation in evaluations]
    measurements = [enrich_measurements(evaluation["measurements"]) for evaluation in evaluations]
    final_counts = Counter(item["final"] for item in verdicts)
    rejected = final_counts.get("rejeitar", 0)
    return {
        "case_count": len(records),
        "completed_case_count": len(records),
        "score": round(mean(scores), 4) if scores else 0.0,
        "score_definition": "Mean per-case score: texture distance from 100%, ratio distance from 1, then fixed pair/brightness/density/NEx penalties.",
        "valid_for_comparison": rejected == 0,
        "final_counts": dict(final_counts),
        "pair_counts": dict(Counter(item["pair_status"] for item in verdicts)),
        "brightness_counts": dict(Counter(item["brightness"] for item in verdicts)),
        "texture_counts": dict(Counter(item["texture"] for item in verdicts)),
        "nex_counts": dict(Counter(item.get("nex_status", "n/a") for item in measurements)),
        "density_counts": dict(Counter(item.get("density_status", "n/a") for item in measurements)),
        "case_scores": {
            evaluation["measurements"]["case_id"]: score
            for evaluation, score in zip(evaluations, scores)
        },
        "numeric_statistics": numeric_statistics(evaluations),
    }


def compare_summaries(current: dict, reference: dict) -> dict:
    current_rejected = int(current["final_counts"].get("rejeitar", 0))
    reference_rejected = int(reference["final_counts"].get("rejeitar", 0))
    delta = round(float(current["score"]) - float(reference["score"]), 4)
    if current_rejected > reference_rejected:
        verdict = "pior"
        reason = "aumentou o número de casos rejeitados"
    elif current_rejected < reference_rejected:
        verdict = "melhor"
        reason = "reduziu o número de casos rejeitados"
    elif delta > 0:
        verdict = "melhor"
        reason = "a nota aumentou sem aumentar rejeições"
    elif delta < 0:
        verdict = "pior"
        reason = "a nota caiu"
    else:
        verdict = "igual"
        reason = "nota e rejeições não mudaram"
    return {
        "verdict": verdict,
        "reason": reason,
        "score_delta": delta,
        "rejected_case_delta": current_rejected - reference_rejected,
    }


def markdown_report(payload: dict) -> str:
    summary = payload["summary"]
    parameters = payload["candidate"]
    lines = [
        f"# Relatório {payload['scope']} · {payload['run']}",
        "",
        f"- Casos: {summary['case_count']}",
        f"- Nota: {summary['score']:.4f}",
        f"- Válido para comparação: {'sim' if summary['valid_for_comparison'] else 'não'}",
        f"- Vereditos finais: {json.dumps(summary['final_counts'], ensure_ascii=False)}",
        f"- Par: {json.dumps(summary['pair_counts'], ensure_ascii=False)}",
        f"- Brilho: {json.dumps(summary['brightness_counts'], ensure_ascii=False)}",
        f"- Textura: {json.dumps(summary['texture_counts'], ensure_ascii=False)}",
        f"- NEx: {json.dumps(summary['nex_counts'], ensure_ascii=False)}",
        "",
        "## Parâmetros",
        "",
        *[f"- {key}: {value}" for key, value in parameters.items()],
    ]
    if payload.get("comparison"):
        comparison = payload["comparison"]
        lines += [
            "",
            "## Comparação",
            "",
            f"- Resultado: **{comparison['verdict']}**",
            f"- Motivo: {comparison['reason']}",
            f"- Diferença da nota: {comparison['score_delta']:+.4f}",
            f"- Diferença de rejeições: {comparison['rejected_case_delta']:+d}",
        ]
    worst = sorted(summary["case_scores"].items(), key=lambda item: item[1])[:5]
    lines += ["", "## Cinco piores casos", "", *[f"- {case_id}: {score:.4f}" for case_id, score in worst]]
    lines += ["", "O JSON ao lado contém todas as métricas de todas as imagens.", ""]
    return "\n".join(lines)


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
