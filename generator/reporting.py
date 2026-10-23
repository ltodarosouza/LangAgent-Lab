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


# Distâncias até a imagem original devolvidas pelo avaliador: 0 = igual à original.
DISTANCE_METRICS = (
    "glcm_contrast_z",
    "glcm_energy_z",
    "wavelet_fine_z",
    "wavelet_coarse_z",
    "wavelet_entropy_z",
    "wavelet_ll_z",
    "nex_delta",
)
PROMOTION_THRESHOLD_PCT = 15.0
METRIC_CAP_PCT = 50.0


def metric_distances(report: dict) -> dict:
    """Média de |métrica| nos casos do lote, por métrica."""
    distances = {}
    for key in DISTANCE_METRICS:
        values = [abs(float(case["evaluation"]["measurements"][key])) for case in report["cases"]]
        distances[key] = mean(values)
    return distances


def metric_improvements(report: dict, baseline: dict) -> dict:
    """Melhora de cada métrica contra o baseline, em %, com teto por métrica."""
    current_cases = sorted(case["case_id"] for case in report["cases"])
    baseline_cases = sorted(case["case_id"] for case in baseline["cases"])
    if current_cases != baseline_cases:
        raise ValueError("o lote e o baseline precisam ter exatamente os mesmos casos")
    current = metric_distances(report)
    reference = metric_distances(baseline)
    improvements = {}
    for key in DISTANCE_METRICS:
        if reference[key] == 0:
            improvement = 0.0 if current[key] == 0 else -100.0
        else:
            improvement = 100.0 * (1.0 - current[key] / reference[key])
        improvements[key] = round(min(improvement, METRIC_CAP_PCT), 4)
    return improvements


def validity_issues(summary: dict) -> tuple[int, int]:
    rejected = int(summary["final_counts"].get("rejeitar", 0))
    pair_issues = int(summary["case_count"]) - int(summary["pair_counts"].get("ok", 0))
    return rejected, pair_issues


def compare_reports(report: dict, baseline: dict, best: dict | None = None) -> dict:
    """Régua única: média de melhora das métricas contra o baseline fixo.

    No lote rápido, `melhor` autoriza os 37 casos. No lote completo, `melhor`
    exige também superar a média da melhor configuração atual (`best`).
    """
    improvements = metric_improvements(report, baseline)
    average = round(mean(improvements.values()), 4)
    rejected, pair_issues = validity_issues(report["summary"])
    baseline_rejected, baseline_pair_issues = validity_issues(baseline["summary"])
    best_average = None
    if best is not None:
        best_average = round(mean(metric_improvements(best, baseline).values()), 4)

    if rejected > baseline_rejected:
        verdict, reason = "pior", "aumentou o número de casos rejeitados em relação ao baseline"
    elif pair_issues > baseline_pair_issues:
        verdict, reason = "pior", "aumentou o número de pares fora de 'ok' em relação ao baseline"
    elif average < PROMOTION_THRESHOLD_PCT:
        verdict = "insuficiente"
        reason = f"melhora média {average:+.1f}% abaixo de {PROMOTION_THRESHOLD_PCT:.0f}% contra o baseline"
    elif best_average is not None and average <= best_average:
        verdict = "insuficiente"
        reason = f"melhora média {average:+.1f}% não supera a melhor atual ({best_average:+.1f}%)"
    else:
        verdict = "melhor"
        reason = f"melhora média {average:+.1f}% contra o baseline, sem perder validade"
        if best_average is not None:
            reason += f", acima da melhor atual ({best_average:+.1f}%)"
    return {
        "verdict": verdict,
        "reason": reason,
        "threshold_pct": PROMOTION_THRESHOLD_PCT,
        "metric_cap_pct": METRIC_CAP_PCT,
        "mean_improvement_pct": average,
        "metric_improvement_pct": improvements,
        "best_mean_improvement_pct": best_average,
        "rejected_case_delta": rejected - baseline_rejected,
        "pair_issue_delta": pair_issues - baseline_pair_issues,
        "score_delta": round(float(report["summary"]["score"]) - float(baseline["summary"]["score"]), 4),
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
            f"- Melhora média contra o baseline: {comparison['mean_improvement_pct']:+.2f}% "
            f"(limite {comparison['threshold_pct']:.0f}%, teto por métrica {comparison['metric_cap_pct']:.0f}%)",
            *[f"  - {key}: {value:+.2f}%" for key, value in comparison["metric_improvement_pct"].items()],
            f"- Diferença de rejeições: {comparison['rejected_case_delta']:+d}",
            f"- Diferença de pares fora de ok: {comparison['pair_issue_delta']:+d}",
            f"- Diferença da nota (só informativa): {comparison['score_delta']:+.4f}",
        ]
        if comparison.get("best_mean_improvement_pct") is not None:
            lines.append(f"- Melhora média da melhor atual: {comparison['best_mean_improvement_pct']:+.2f}%")
    worst = sorted(summary["case_scores"].items(), key=lambda item: item[1])[:5]
    lines += ["", "## Cinco piores casos", "", *[f"- {case_id}: {score:.4f}" for case_id, score in worst]]
    lines += ["", "O JSON ao lado contém todas as métricas de todas as imagens.", ""]
    return "\n".join(lines)


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))
