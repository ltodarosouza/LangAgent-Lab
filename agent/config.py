import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SEARCH_SPACE_PATH = ROOT / "configs" / "search_space.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_candidate(candidate: dict, search_space: dict | None = None) -> dict:
    search_space = search_space or load_json(SEARCH_SPACE_PATH)
    expected = set(search_space)
    missing = expected - set(candidate)
    extra = set(candidate) - expected
    if missing or extra:
        raise ValueError(f"campos inválidos; ausentes={sorted(missing)}, extras={sorted(extra)}")

    validated = {}
    for name, rule in search_space.items():
        value = candidate[name]
        expected_type = rule.get("type")
        type_ok = {
            "integer": isinstance(value, int) and not isinstance(value, bool),
            "number": isinstance(value, (int, float)) and not isinstance(value, bool),
            "string": isinstance(value, str),
        }.get(expected_type, False)
        if not type_ok:
            raise ValueError(f"{name}={value!r} não é do tipo {expected_type!r}")
        if "choices" in rule and value not in rule["choices"]:
            raise ValueError(f"{name}={value!r} fora das opções {rule['choices']}")
        if "min" in rule and value < rule["min"]:
            raise ValueError(f"{name}={value!r} abaixo do mínimo {rule['min']}")
        if "max" in rule and value > rule["max"]:
            raise ValueError(f"{name}={value!r} acima do máximo {rule['max']}")
        validated[name] = value
    return validated
