from statistics import mean


def score_cases(cases: list[dict]) -> dict:
    invalid = 0
    case_scores = []
    for case in cases:
        verdicts = case["verdicts"]
        values = case["measurements"]
        valid = verdicts["brightness"] == "aprovada" and verdicts["pair_status"] == "ok"
        if not valid:
            invalid += 1
        texture_error = mean(
            abs(values[name] - 100.0)
            for name in ("wavelet_fine_pct", "wavelet_coarse_pct", "glcm_contrast_pct")
        )
        correlation_penalty = max(0.0, 0.95 - values["pair_correlation"]) * 100.0
        nex_penalty = 8.0 if values["nex_status"] != "ok" else 0.0
        case_score = max(0.0, 100.0 - texture_error - correlation_penalty - nex_penalty)
        if not valid:
            case_score = 0.0
        case_scores.append(case_score)

    return {
        "score": round(mean(case_scores), 4),
        "valid": invalid == 0,
        "invalid_cases": invalid,
        "approved_cases": sum(case["verdicts"]["final"] == "aprovada" for case in cases),
        "case_count": len(cases),
    }
