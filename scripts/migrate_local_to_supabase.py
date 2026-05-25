"""
Migration des données locales vers Supabase.

Prérequis :
  - SUPABASE_URL et SUPABASE_SERVICE_ROLE_KEY dans .env.local (ou variables d'env)
  - Schéma SQL appliqué dans Supabase (supabase/schema.sql)
  - Bucket "chords-exports" créé dans Supabase Storage (public)
  - pip install supabase

Usage :
  python scripts/migrate_local_to_supabase.py --dry-run    # simule sans modifier
  python scripts/migrate_local_to_supabase.py              # migration réelle
"""

import argparse
import io
import json
import sys
import unicodedata
from pathlib import Path


def _ascii_key(slug: str, filename: str) -> str:
    """Clé Storage ASCII-safe (Supabase/S3 rejette les caractères non-ASCII)."""
    safe = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode("ascii")
    return f"{slug}/{safe}"

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR / "scripts"))
sys.path.insert(0, str(ROOT_DIR))


def _load_env() -> None:
    """Charge .env.local dans os.environ."""
    import os
    env_path = ROOT_DIR / ".env.local"
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))


def _check_env() -> None:
    import os
    missing = [v for v in ("SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY") if not os.environ.get(v)]
    if missing:
        print(f"ERREUR : variables manquantes : {', '.join(missing)}")
        print("→ Créez .env.local à la racine du projet (voir .env.example).")
        sys.exit(1)


def migrate(dry_run: bool = True) -> None:
    import os
    _load_env()
    _check_env()

    try:
        from supabase import create_client
    except ImportError:
        print("ERREUR : 'supabase' non installé. Installez avec : pip install supabase")
        sys.exit(1)

    from config import DATA_DIR, PDF_EXPORT_DIR

    url    = os.environ["SUPABASE_URL"]
    key    = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    bucket = os.environ.get("SUPABASE_STORAGE_BUCKET", "chords-exports")
    client = create_client(url, key)

    mode = "[DRY-RUN]" if dry_run else "[RÉEL]"
    print(f"\n{'='*60}")
    print(f"Migration Chords → Supabase  {mode}")
    print(f"{'='*60}")
    print(f"  Supabase URL    : {url}")
    print(f"  Storage bucket  : {bucket}")
    print(f"  Data dir        : {DATA_DIR}")
    print(f"  PDF export dir  : {PDF_EXPORT_DIR}")
    print()

    # -----------------------------------------------------------------------
    # 1. Chansons (data/song_*.json)
    # -----------------------------------------------------------------------
    print("── 1. Chansons ──────────────────────────────────────────")
    songs_ok = 0
    songs_err: list[tuple[str, str]] = []
    song_slugs: dict[str, dict] = {}  # slug → song dict

    for json_path in sorted(DATA_DIR.glob("song_*.json")):
        try:
            song = json.loads(json_path.read_text(encoding="utf-8"))
            meta = song.get("meta", {})
            slug = meta.get("slug", json_path.stem.removeprefix("song_"))
            song_slugs[slug] = song
            print(f"  ✓ {slug:40s} « {meta.get('title', '?')} »")
            if not dry_run:
                client.table("songs").upsert({
                    "slug":              slug,
                    "title":             meta.get("title", ""),
                    "artist":            meta.get("artist", ""),
                    "album":             meta.get("album"),
                    "key":               meta.get("key"),
                    "capo":              meta.get("capo", 0),
                    "tempo":             meta.get("tempo", 0),
                    "review_status":     song.get("review_status", ""),
                    "validation_status": song.get("validation", {}).get("status", "pending"),
                    "song_json":         song,
                }, on_conflict="slug").execute()
            songs_ok += 1
        except Exception as exc:
            err = str(exc)
            print(f"  ✗ {json_path.name}: {err}")
            songs_err.append((json_path.name, err))

    print(f"\n  → {songs_ok} chansons migrées, {len(songs_err)} erreurs\n")

    # -----------------------------------------------------------------------
    # 2. Backups (data/backups/<slug>/*.json)
    # -----------------------------------------------------------------------
    print("── 2. Backups ───────────────────────────────────────────")
    backup_dir = DATA_DIR / "backups"
    backups_ok  = 0
    backups_err: list[tuple[str, str]] = []

    if not backup_dir.exists():
        print("  (Aucun dossier data/backups/ trouvé — ignoré)\n")
    else:
        for slug_dir in sorted(backup_dir.iterdir()):
            if not slug_dir.is_dir():
                continue
            slug = slug_dir.name

            song_id: str | None = None
            if not dry_run:
                resp = client.table("songs").select("id").eq("slug", slug).execute()
                if not resp.data:
                    print(f"  ⚠ Chanson '{slug}' introuvable dans Supabase — backups ignorés")
                    continue
                song_id = resp.data[0]["id"]

            for bfile in sorted(slug_dir.glob("*.json")):
                try:
                    bsong = json.loads(bfile.read_text(encoding="utf-8"))
                    print(f"  ✓ {slug}/{bfile.name}")
                    if not dry_run and song_id:
                        client.table("song_backups").insert({
                            "song_id":   song_id,
                            "slug":      slug,
                            "song_json": bsong,
                            "reason":    "migration",
                        }).execute()
                    backups_ok += 1
                except Exception as exc:
                    err = str(exc)
                    print(f"  ✗ {slug}/{bfile.name}: {err}")
                    backups_err.append((f"{slug}/{bfile.name}", err))

        print(f"\n  → {backups_ok} backups migrés, {len(backups_err)} erreurs\n")

    # -----------------------------------------------------------------------
    # 3. PDFs exportés (PDF_EXPORT_DIR)
    # -----------------------------------------------------------------------
    print("── 3. PDFs exportés ─────────────────────────────────────")
    pdfs_ok  = 0
    pdfs_err: list[tuple[str, str]] = []

    if not PDF_EXPORT_DIR.exists():
        print(f"  (Dossier {PDF_EXPORT_DIR} introuvable — ignoré)\n")
    else:
        from generate_docx import _split_pdf_filename

        # Index slug → noms de fichiers PDF attendus
        slug_to_filenames: dict[str, dict[str, str]] = {
            slug: {
                "chords": _split_pdf_filename(song, "chords"),
                "memo":   _split_pdf_filename(song, "memo"),
            }
            for slug, song in song_slugs.items()
        }

        for pdf_path in sorted(PDF_EXPORT_DIR.glob("*.pdf")):
            # Trouver le slug correspondant
            matched_slug = None
            matched_part = None
            for slug, parts in slug_to_filenames.items():
                for part, fname in parts.items():
                    if fname == pdf_path.name:
                        matched_slug = slug
                        matched_part = part
                        break
                if matched_slug:
                    break

            if not matched_slug:
                print(f"  ⚠ {pdf_path.name} — slug inconnu, ignoré")
                continue

            print(f"  ✓ {pdf_path.name} → {matched_slug}/{pdf_path.name}")
            if not dry_run:
                try:
                    data_bytes = pdf_path.read_bytes()
                    client.storage.from_(bucket).upload(
                        _ascii_key(matched_slug, pdf_path.name),
                        data_bytes,
                        {"content-type": "application/pdf", "upsert": "true"},
                    )
                    flag_col = "has_pdf_chords" if matched_part == "chords" else "has_pdf_memo"
                    client.table("songs").update({flag_col: True}).eq("slug", matched_slug).execute()
                    pdfs_ok += 1
                except Exception as exc:
                    err = str(exc)
                    print(f"  ✗ {pdf_path.name}: {err}")
                    pdfs_err.append((pdf_path.name, err))
            else:
                pdfs_ok += 1

    print(f"\n  → {pdfs_ok} PDFs migrés, {len(pdfs_err)} erreurs\n")

    # -----------------------------------------------------------------------
    # Rapport final
    # -----------------------------------------------------------------------
    print(f"{'='*60}")
    total_err = len(songs_err) + len(backups_err) + len(pdfs_err)
    if dry_run:
        print(f"  DRY-RUN terminé. Aucune modification effectuée.")
        print(f"  Relancez sans --dry-run pour migrer réellement.")
    else:
        print(f"  Migration terminée.")
    print(f"  Erreurs totales : {total_err}")
    if total_err:
        print("  Détail :")
        for name, err in songs_err + backups_err + pdfs_err:
            print(f"    ✗ {name} : {err}")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Migration données locales → Supabase",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Simule la migration sans rien écrire dans Supabase.",
    )
    args = parser.parse_args()
    migrate(dry_run=args.dry_run)
