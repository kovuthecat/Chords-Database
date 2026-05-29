"""Utilitaires rythme : normalisation de saisie, chargement des présets."""
import json
from pathlib import Path

_CHAR_MAP = {'d': '↓', 'u': '↑'}
_PRESETS_FILE = Path(__file__).parent.parent / "static" / "rhythm_patterns.json"
_presets_cache = None


def normalize_rhythm_input(text: str) -> str:
    """Convertit les raccourcis clavier en caractères Unicode.
    d→↓  u→↑  (espaces et autres caractères conservés)
    Exemple : 'd du udu' → '↓ ↓↑ ↑↓↑'
    """
    return "".join(_CHAR_MAP.get(c, c) for c in text)


def load_presets() -> list:
    """Charge et met en cache la bibliothèque de présets depuis static/rhythm_patterns.json."""
    global _presets_cache
    if _presets_cache is None:
        try:
            with open(_PRESETS_FILE, encoding="utf-8") as f:
                _presets_cache = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            _presets_cache = []
    return _presets_cache


def get_preset_by_id(preset_id: str) -> dict | None:
    """Retourne le préset correspondant à l'id, ou None si introuvable."""
    for p in load_presets():
        if p.get("id") == preset_id:
            return p
    return None
