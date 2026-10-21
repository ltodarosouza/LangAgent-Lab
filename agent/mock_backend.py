import hashlib


MOCK_CASES = (
    "mock-lung-001",
    "mock-lung-002",
    "mock-lung-003",
    "mock-lung-004",
    "mock-lung-005",
)


def case_offset(case_id: str) -> float:
    digest = hashlib.sha256(case_id.encode()).digest()
    return (digest[0] / 255.0 - 0.5) * 4.0


def simulate_case(case_id: str, candidate: dict) -> dict:
    """Deterministic stand-in for LDM generation plus texture evaluation."""
    steps = float(candidate["steps"])
    noise = float(candidate["noise_level"])
    sampler = candidate["sampler"]
    offset = case_offset(case_id)
    sampler_shift = 0.8 if sampler == "ddpm" else 0.0

    distance = abs(steps - (34.0 + offset))
    noise_penalty = abs(noise - 1.0)
    fine = 100.0 - 0.34 * distance - 1.7 * noise_penalty - sampler_shift
    coarse = 100.0 - 0.25 * distance - 1.2 * noise_penalty - 0.5 * sampler_shift
    contrast = 100.0 - 0.31 * distance - 1.5 * noise_penalty - sampler_shift
    delta_mu = 0.002 * offset + 0.004 * noise_penalty
    correlation = 0.985 - 0.0007 * distance - 0.002 * noise_penalty
    nex_status = "alto" if steps < 15 or noise > 8 else "ok"

    texture_ok = all(80.0 <= value <= 125.0 for value in (fine, coarse, contrast)) and nex_status == "ok"
    brightness_ok = abs(delta_mu) <= 0.10
    pair_ok = correlation >= 0.5
    final = "aprovada" if texture_ok and brightness_ok and pair_ok else "revisar" if pair_ok else "rejeitar"
    reasons = []
    if not texture_ok:
        reasons.append("textura fora do esperado")
    if not brightness_ok:
        reasons.append("brilho fora do esperado")
    if not pair_ok:
        reasons.append("par suspeito")

    return {
        "case_id": case_id,
        "verdicts": {
            "final": final,
            "final_reasons": "; ".join(reasons) or "brilho e textura dentro do esperado",
            "pair_status": "ok" if pair_ok else "suspeito",
            "brightness": "aprovada" if brightness_ok else "revisão",
            "texture": "aprovada" if texture_ok else "revisão",
        },
        "measurements": {
            "wavelet_fine_pct": round(fine, 6),
            "wavelet_coarse_pct": round(coarse, 6),
            "glcm_contrast_pct": round(contrast, 6),
            "delta_mu": round(delta_mu, 6),
            "pair_correlation": round(correlation, 6),
            "nex_status": nex_status,
        },
    }


def run_mock(candidate: dict) -> list[dict]:
    return [simulate_case(case_id, candidate) for case_id in MOCK_CASES]
