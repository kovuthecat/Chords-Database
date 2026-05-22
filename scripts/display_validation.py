"""
Affiche le brouillon de validation d'un fichier song JSON et demande la validation utilisateur.
Met à jour validation.status = "user_validated" dans le JSON après confirmation.

Usage : python scripts/display_validation.py data/song_<slug>.json
"""

import io
import json
import sys
from pathlib import Path
from datetime import datetime


def _ensure_utf8():
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


CONFIRM_WORDS = {"ok", "oui", "yes", "valider", "valide", "go", "o"}
SEP = "─" * 58


def load_song(json_path: str) -> dict:
    path = Path(json_path)
    if not path.exists():
        print(f"Erreur : fichier introuvable : {json_path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_song(song: dict, json_path: str):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(song, f, ensure_ascii=False, indent=2)


def confidence_bar(score: float, width: int = 10) -> str:
    filled = round(score * width)
    return "█" * filled + "░" * (width - filled)


def confidence_label(score: float) -> str:
    if score >= 0.85:
        return "Élevé"
    elif score >= 0.60:
        return "Moyen"
    else:
        return "Faible"


def display_draft(song: dict):
    meta = song["meta"]
    conf = song.get("confidence", {})
    sources = song.get("sources", [])
    sections = song.get("sections", [])
    sequence = [
        x for x in song.get("structure_sequence", [])
        if not (isinstance(x, str) and x.startswith("_comment"))
    ]
    warnings = song.get("warnings", [])
    variants = song.get("variants", [])
    corrections = song.get("validation", {}).get("user_corrections", [])

    print()
    print("╔" + "═" * 56 + "╗")
    header = f"  VALIDATION — {meta.get('title', '?')} — {meta.get('artist', '?')}  "
    print("║" + header[:56].center(56) + "║")
    print("╚" + "═" * 56 + "╝")
    print()

    # --- Métadonnées ---
    print("MÉTADONNÉES")
    print(SEP)
    key = meta.get("key", "?")
    mode = "majeur" if meta.get("key_mode") == "major" else "mineur"
    capo = meta.get("capo", 0)
    capo_str = str(capo) if capo and capo > 0 else "aucun"

    print(f"  Tonalité   : {key} {mode}")
    print(f"  Capo       : {capo_str}")
    if meta.get("tempo"):
        print(f"  Tempo      : ≈ {meta['tempo']} bpm")
    if meta.get("tuning") and meta["tuning"] != "standard":
        print(f"  Accordage  : {meta['tuning']}")
    if meta.get("time_signature"):
        print(f"  Mesure     : {meta['time_signature']}")
    if meta.get("version"):
        print(f"  Version    : {meta['version']}")
    print()

    # --- Structure ---
    print("STRUCTURE DU MORCEAU")
    print(SEP)

    sections_by_id = {s["id"]: s for s in sections}

    if sequence:
        seen = set()
        for section_id in sequence:
            section = sections_by_id.get(section_id)
            if not section:
                print(f"  [? {section_id}]  ← section non trouvée dans sections[]")
                continue

            label = section.get("label", section.get("type", section_id))
            is_instr = section.get("is_instrumental", False)
            chord_grid = section.get("chord_grid", "")
            repeats = section.get("repeats", 1)

            if section_id in seen:
                print(f"  → {label} (reprise)")
            else:
                parts = [f"  [{label}]"]
                if is_instr:
                    parts.append("[instrumental]")
                if repeats > 1:
                    parts.append(f"×{repeats}")
                if chord_grid:
                    parts.append(f" {chord_grid}")
                print("  ".join(parts))
                seen.add(section_id)
    else:
        for section in sections:
            label = section.get("label", section.get("type", "?"))
            print(f"  [{label}]")

    print()

    # --- Accords ---
    chords = [c for c in song.get("chords_used", []) if not c.startswith("_comment")]
    if chords:
        print("ACCORDS UTILISÉS")
        print(SEP)
        print(f"  {' '.join(chords)}")
        print()

    # --- Scoring de confiance ---
    print("SCORING DE CONFIANCE")
    print(SEP)
    score_fields = [
        ("Structure globale",      conf.get("structure", 0)),
        ("Accords",                conf.get("chords", 0)),
        ("Capo",                   conf.get("capo", 0)),
        ("Sections instrumentales",conf.get("instrumental_sections", 0)),
        ("Placement paroles",      conf.get("lyric_alignment", 0)),
    ]
    for label, score in score_fields:
        bar = confidence_bar(score)
        pct = int(score * 100)
        lvl = confidence_label(score)
        print(f"  {label:<26} {bar} {pct:3d}%  [{lvl}]")

    overall = conf.get("overall", 0)
    print(SEP)
    bar = confidence_bar(overall)
    pct = int(overall * 100)
    lvl = confidence_label(overall)
    print(f"  {'SCORE GLOBAL':<26} {bar} {pct:3d}%  [{lvl}]")
    print()

    # --- Avertissements ---
    if warnings:
        print("AVERTISSEMENTS")
        print(SEP)
        sev_prefix = {"high": "⚠ HAUT  ", "medium": "⚠ MOYEN ", "low": "ℹ FAIBLE"}
        for w in warnings:
            prefix = sev_prefix.get(w.get("severity", "low"), "ℹ ")
            section_tag = f"[{w['section']}] " if w.get("section") else ""
            print(f"  {prefix} {section_tag}{w['message']}")
        print()

    # --- Variantes ---
    if variants:
        print("VARIANTES DISPONIBLES")
        print(SEP)
        for v in variants:
            print(f"  • {v['name']} : {v.get('differences', '')}")
        print()

    # --- Sources ---
    if sources:
        print("SOURCES UTILISÉES")
        print(SEP)
        for s in sources:
            notes = f" — {s['notes']}" if s.get("notes") else ""
            print(f"  ✓ {s['name']}{notes}")
        print()

    # --- Corrections précédentes ---
    if corrections:
        print("CORRECTIONS NOTÉES")
        print(SEP)
        for i, c in enumerate(corrections, 1):
            print(f"  {i}. {c}")
        print()

    # --- Invite ---
    print(SEP)
    print()
    print("  Vérifier : structure · accords · tonalité · capo · sections instrumentales")
    if variants:
        print("  Préciser si tu veux utiliser une variante particulière.")
    print()
    print("  → Tape  ok       pour valider et générer le DOCX.")
    print("  → Ou décris une correction : 'capo 2', 'Am au lieu de A', 'ajoute pont', etc.")
    print()


def ask_user() -> str:
    try:
        return input("  Réponse : ").strip()
    except (EOFError, KeyboardInterrupt):
        print("\n  Interruption — fichier non modifié.")
        sys.exit(0)


def run_validation_loop(song: dict, json_path: str):
    while True:
        display_draft(song)
        answer = ask_user()

        if answer.lower() in CONFIRM_WORDS:
            _validate(song, json_path)
            break

        if not answer:
            continue

        # L'utilisateur a décrit une correction
        song.setdefault("validation", {}).setdefault("user_corrections", []).append(answer)
        print()
        print(f"  ✎  Correction notée : « {answer} »")
        print("     Applique la correction dans le JSON, puis relance ce script.")
        print("     Ou continue à noter ici d'autres corrections.")
        print()

        while True:
            extra = ask_user()
            if extra.lower() in CONFIRM_WORDS:
                _validate(song, json_path)
                return
            if not extra:
                save_song(song, json_path)
                print()
                print("  Corrections sauvegardées dans le JSON.")
                print("  Relance le script après avoir appliqué les corrections.")
                print()
                return
            song["validation"]["user_corrections"].append(extra)
            print(f"  ✎  Correction notée : « {extra} »")


def _validate(song: dict, json_path: str):
    song.setdefault("validation", {})
    song["validation"]["status"] = "user_validated"
    song["validation"]["validated_at"] = datetime.now().isoformat()
    save_song(song, json_path)
    slug = song["meta"].get("slug", "slug")
    print()
    print("  ✓  Validation enregistrée.")
    print()
    print("  Lance maintenant :")
    print(f"     python scripts/generate_docx.py {json_path}")
    print()


def main():
    _ensure_utf8()
    if len(sys.argv) < 2:
        print("Usage : python scripts/display_validation.py data/song_<slug>.json")
        sys.exit(1)

    json_path = sys.argv[1]
    song = load_song(json_path)

    # Déjà validé ?
    val = song.get("validation", {})
    if val.get("status") == "user_validated":
        validated_at = val.get("validated_at", "?")
        print(f"\n  Ce fichier est déjà validé (le {validated_at}).")
        print("  Lance directement :")
        print(f"     python scripts/generate_docx.py {json_path}\n")
        sys.exit(0)

    run_validation_loop(song, json_path)


if __name__ == "__main__":
    main()
