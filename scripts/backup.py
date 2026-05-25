"""
Backup automatique des JSON chanson avant chaque sauvegarde.
Appelé par _save_song() dans app.py.

Structure :
    data/backups/<slug>/
        2026-05-25_14-32-10.json
        2026-05-25_14-41-03.json
"""
import json
from datetime import datetime
from pathlib import Path

from config import DATA_DIR

BACKUP_DIR = DATA_DIR / "backups"
MAX_BACKUPS = 20


def create_backup(song_path: Path) -> Path | None:
    """Copie timestampée du JSON avant écrasement. Ne jamais écraser un backup existant."""
    if not song_path.exists():
        return None
    slug = song_path.stem.removeprefix("song_")
    backup_dir = BACKUP_DIR / slug
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = backup_dir / f"{ts}.json"
    # Éviter les collisions si plusieurs sauvegardes dans la même seconde
    counter = 0
    while dest.exists():
        counter += 1
        dest = backup_dir / f"{ts}_{counter}.json"
    dest.write_bytes(song_path.read_bytes())
    cleanup_old_backups(slug)
    return dest


def list_backups(slug: str) -> list[dict]:
    """Liste des backups pour un slug, du plus récent au plus ancien."""
    backup_dir = BACKUP_DIR / slug
    if not backup_dir.exists():
        return []
    files = sorted(backup_dir.glob("*.json"), reverse=True)
    return [
        {
            "filename": f.name,
            "timestamp": f.stem,
            "size_kb": round(f.stat().st_size / 1024, 1),
        }
        for f in files
    ]


def restore_backup(slug: str, backup_filename: str) -> dict | None:
    """Charge un backup et retourne son contenu JSON. None si introuvable ou invalide."""
    # Sécurité : interdire tout path traversal
    backup_path = (BACKUP_DIR / slug / backup_filename).resolve()
    expected_dir = (BACKUP_DIR / slug).resolve()
    if not str(backup_path).startswith(str(expected_dir)):
        return None
    if not backup_path.exists():
        return None
    with open(backup_path, encoding="utf-8") as f:
        return json.load(f)


def cleanup_old_backups(slug: str, max_keep: int = MAX_BACKUPS) -> None:
    """Supprime les backups les plus anciens au-delà de max_keep."""
    backup_dir = BACKUP_DIR / slug
    if not backup_dir.exists():
        return
    files = sorted(backup_dir.glob("*.json"))  # du plus ancien au plus récent
    surplus = files[:-max_keep] if len(files) > max_keep else []
    for f in surplus:
        f.unlink(missing_ok=True)
