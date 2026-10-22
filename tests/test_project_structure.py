import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from app.domains.appointments.intent_classifier import classify_intent
from app.infrastructure.config.config_loader import load_clinic, load_guardrails


def test_domain_modules_are_importable():
    result = classify_intent("Quero cancelar minha consulta")
    assert result["intent"] == "CANCEL"


def test_config_module_is_importable():
    config = load_guardrails()
    assert config["default_intent"] == "UNKNOWN"


def test_clinic_units_are_canonical():
    clinic = load_clinic()
    ids = {unit["id"]: unit["ddd"] for unit in clinic["units"]}
    assert ids["pato-branco"] == "46"
    assert ids["sao-carlos"] == "16"
    assert clinic["practice"]["specialty"] == "harmonizacao-orofacial"


def _layout():
    return json.loads((ROOT / "docs" / "governance" / "layout.json").read_text(encoding="utf-8"))


def _tracked_root_entries():
    try:
        out = subprocess.run(
            ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return None
    return {line.split("/")[0] for line in out if line}


def test_required_paths_exist():
    missing = [p for p in _layout()["required"] if not (ROOT / p).exists()]
    assert not missing, f"faltando na estrutura canônica: {missing}"


def test_forbidden_paths_are_gone():
    present = [p for p in _layout()["forbidden"] if (ROOT / p).exists()]
    assert not present, f"caminhos removidos voltaram: {present}"


def test_root_only_has_canonical_entries():
    entries = _tracked_root_entries()
    if entries is None:
        return
    extra = sorted(entries - set(_layout()["root_allowed"]))
    assert not extra, f"itens fora do contrato na raiz (docs/governance/layout.json): {extra}"
