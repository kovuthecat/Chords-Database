"""
CLI Chords (v2) — pipeline simplifié JSON → DOCX / PDF.

Workflow principal : utiliser l'interface web (python app.py).
Ce script est utile pour un usage en ligne de commande ou les scripts automatisés.

Usage :
  python main.py data/song_<slug>.json            ← génère DOCX + PDF dans output/
  python main.py data/song_<slug>.json --split-pdf ← génère + exporte 2 PDFs séparés
  python main.py --list                            ← liste les chansons disponibles
  python main.py --validate data/song_<slug>.json  ← valide le JSON seulement
"""

from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

ROOT_DIR    = Path(__file__).parent
SCRIPTS_DIR = ROOT_DIR / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


def _ensure_utf8() -> None:
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def list_songs() -> None:
    from config import DATA_DIR, OUTPUT_DIR

    jsons = sorted(DATA_DIR.glob("song_*.json"))
    if not jsons:
        print("Aucune chanson dans data/.")
        return

    col_w = [32, 22, 12, 8, 8]
    header = (
        f"{'Titre / Artiste':<{col_w[0]}} "
        f"{'Slug':<{col_w[1]}} "
        f"{'Statut':<{col_w[2]}} "
        f"{'Score':<{col_w[3]}} "
        f"{'DOCX':<{col_w[4]}}"
    )
    sep = "-" * (sum(col_w) + len(col_w) - 1)
    print()
    print(header)
    print(sep)

    for path in jsons:
        try:
            with open(path, encoding="utf-8") as f:
                song = json.load(f)
        except Exception:
            print(f"  {path.name} — erreur de lecture")
            continue

        meta   = song.get("meta", {})
        title  = meta.get("title", "?")
        artist = meta.get("artist", "?")
        slug   = meta.get("slug", path.stem.removeprefix("song_"))
        label  = f"{title} / {artist}"

        val    = song.get("validation", {}).get("status", "pending")
        status = "validé" if val == "user_validated" else ("rejeté" if val == "rejected" else "pending")

        conf  = song.get("confidence", {}).get("overall", 0)
        score = f"{int(conf * 100)}%" if conf else "—"

        docx  = "oui" if (OUTPUT_DIR / f"song_{slug}.docx").exists() else "-"

        print(
            f"{label[:col_w[0]]:<{col_w[0]}} "
            f"{slug[:col_w[1]]:<{col_w[1]}} "
            f"{status:<{col_w[2]}} "
            f"{score:<{col_w[3]}} "
            f"{docx:<{col_w[4]}}"
        )

    print(sep)
    print(f"  {len(jsons)} chanson(s)\n")


def main() -> None:
    _ensure_utf8()

    parser = argparse.ArgumentParser(
        description="Chords CLI — JSON → DOCX / PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Exemples :
  python main.py data/song_moriarty-jimmy.json
  python main.py data/song_moriarty-jimmy.json --split-pdf  # 2 PDFs
  python main.py --validate data/song_moriarty-jimmy.json
  python main.py --list

Pour l'interface web : python app.py  → http://localhost:5000
""",
    )
    parser.add_argument(
        "json_path", nargs="?", metavar="FICHIER",
        help="Chemin vers le JSON chanson (data/song_<slug>.json)",
    )
    parser.add_argument(
        "--split-pdf", action="store_true",
        help="Exporte 2 PDFs séparés dans PDF_EXPORT_DIR après génération (Paroles & Accords + Mémo Guitare)",
    )
    parser.add_argument(
        "--validate", metavar="FICHIER", dest="validate_path",
        help="Valide uniquement le JSON (sans générer)",
    )
    parser.add_argument(
        "--list", action="store_true", dest="list_mode",
        help="Liste toutes les chansons disponibles",
    )
    args = parser.parse_args()

    from config import DATA_DIR, OUTPUT_DIR
    from validate_song_json import validate_song_json

    if args.list_mode:
        list_songs()
        return

    # Validation seule
    if args.validate_path:
        path = Path(args.validate_path)
        if not path.exists():
            print(f"Erreur : fichier introuvable : {path}")
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            song = json.load(f)
        errors = validate_song_json(song)
        if errors:
            print(f"Validation échouée ({len(errors)} erreur(s)) :")
            for e in errors:
                print(f"  • {e}")
            sys.exit(1)
        print(f"OK — JSON valide : {path.name}")
        return

    # Génération DOCX + PDF
    if not args.json_path:
        parser.print_help()
        sys.exit(1)

    path = Path(args.json_path)
    if not path.exists():
        print(f"Erreur : fichier introuvable : {path}")
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        song = json.load(f)

    errors = validate_song_json(song)
    if errors:
        print(f"JSON invalide ({len(errors)} erreur(s)) — génération annulée :")
        for e in errors:
            print(f"  • {e}")
        sys.exit(1)

    from generate_docx import generate, generate_pdf, generate_split_pdf

    slug = song["meta"].get("slug", "output")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    docx_path = OUTPUT_DIR / f"song_{slug}.docx"
    generate(song, docx_path)

    try:
        pdf_path = OUTPUT_DIR / f"song_{slug}.pdf"
        generate_pdf(song, pdf_path)
    except Exception as e:
        print(f"Avertissement PDF : {e}")

    if args.split_pdf:
        from datetime import datetime
        song.setdefault("validation", {})
        song["validation"]["status"] = "user_validated"
        song["validation"]["validated_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(song, f, ensure_ascii=False, indent=2)
        generate_split_pdf(song, slug)


if __name__ == "__main__":
    main()
