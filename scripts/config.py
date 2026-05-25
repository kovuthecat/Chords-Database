"""
Chemins centralisés et configuration du projet Chords.
Importé par generate_docx.py, app.py, storage.py et main.py.
Fonctionne depuis n'importe quel répertoire de travail.

PDF_EXPORT_DIR est configurable via .env.local (à la racine du repo) :
    PDF_EXPORT_DIR=C:\\Users\\kovu\\SynologyDrive\\Thibault\\Guitartabs\\Chords

Backend de stockage :
    STORAGE_BACKEND=local     (défaut — fichiers locaux)
    STORAGE_BACKEND=supabase  (Supabase Postgres + Storage)
"""
import os
from pathlib import Path

ROOT_DIR    = Path(__file__).parent.parent   # racine du repo
DATA_DIR    = ROOT_DIR / "data"              # fichiers song_*.json
OUTPUT_DIR  = ROOT_DIR / "output"           # DOCX et PDF générés
SCRIPTS_DIR = ROOT_DIR / "scripts"


def _read_env_local() -> dict[str, str]:
    """Lit les variables de .env.local sans dépendance python-dotenv."""
    env_path = ROOT_DIR / ".env.local"
    env: dict[str, str] = {}
    if not env_path.exists():
        return env
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip().strip('"').strip("'")
    return env


_env = _read_env_local()

# Pousser les variables de .env.local dans os.environ pour les modules qui lisent os.environ
for _k, _v in _env.items():
    os.environ.setdefault(_k, _v)

# PDF_EXPORT_DIR : .env.local > variable d'environnement > valeur par défaut
_pdf_export_raw = (
    _env.get("PDF_EXPORT_DIR")
    or os.environ.get("PDF_EXPORT_DIR")
)
PDF_EXPORT_DIR = (
    Path(_pdf_export_raw)
    if _pdf_export_raw
    else Path(r"C:\Users\kovu\SynologyDrive\Thibault\Guitartabs\Chords")
)

# Backend de stockage
STORAGE_BACKEND: str = (
    _env.get("STORAGE_BACKEND")
    or os.environ.get("STORAGE_BACKEND", "local")
)
