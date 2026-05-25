"""
Validation du JSON chanson entrant.
Appelé par app.py avant toute génération.
Usage CLI : python scripts/validate_song_json.py data/song_<slug>.json
"""
import json
import re
import sys
from pathlib import Path

# Regex : slug = lettres minuscules, chiffres, tirets, underscores
_SLUG_RE = re.compile(r'^[a-z0-9_-]+$')
# Regex : section ID = alphanumérique + tirets + underscores (pas d'espaces ni de /)
_SECTION_ID_RE = re.compile(r'^[a-zA-Z0-9_-]+$')


def validate_song_json(song: dict) -> list[str]:
    """Valide la structure d'un dict song. Retourne la liste des erreurs (vide = valide)."""
    errors = []

    # --- meta ---
    meta = song.get("meta")
    if not isinstance(meta, dict):
        errors.append("meta : champ manquant ou invalide")
        return errors  # impossible de continuer sans meta
    if not meta.get("title"):
        errors.append("meta.title est requis")
    if not meta.get("artist"):
        errors.append("meta.artist est requis")
    slug = meta.get("slug")
    if not slug:
        errors.append("meta.slug est requis")
    elif not _SLUG_RE.match(slug):
        errors.append(
            f"meta.slug invalide '{slug}' — utiliser uniquement [a-z0-9_-] "
            "(pas d'espaces, majuscules, ni caractères spéciaux)"
        )

    # --- sections ---
    sections = song.get("sections")
    if not isinstance(sections, list) or len(sections) == 0:
        errors.append("sections est requis et ne peut pas être vide")
        return errors  # impossible de valider la cohérence sans sections

    section_ids = set()
    for i, s in enumerate(sections):
        if not isinstance(s, dict):
            errors.append(f"sections[{i}] : doit être un objet")
            continue
        sid = s.get("id")
        if not sid:
            errors.append(f"sections[{i}] : id est requis")
        elif not _SECTION_ID_RE.match(sid):
            errors.append(
                f"sections[{i}].id invalide '{sid}' — utiliser uniquement [a-zA-Z0-9_-]"
            )
        else:
            section_ids.add(sid)

        # Validation positions : entiers, ordre croissant, pas de collision exacte
        for line_i, line in enumerate(s.get("lines", [])):
            chords_in_line = line.get("chords", [])
            positions: list[int] = []
            valid_types = True
            for chord_entry in chords_in_line:
                pos = chord_entry.get("position")
                if pos is not None and not isinstance(pos, int):
                    errors.append(
                        f"Section '{sid}' ligne {line_i} : "
                        f"position d'accord doit être un entier, trouvé : {pos!r}"
                    )
                    valid_types = False
                elif isinstance(pos, int):
                    positions.append(pos)
            if valid_types and len(positions) > 1:
                for j in range(1, len(positions)):
                    if positions[j] == positions[j - 1]:
                        errors.append(
                            f"Section '{sid}' ligne {line_i} : "
                            f"collision de positions ({positions[j]}) — deux accords à la même position"
                        )
                        break
                    if positions[j] < positions[j - 1]:
                        errors.append(
                            f"Section '{sid}' ligne {line_i} : "
                            f"positions non ordonnées ({positions[j-1]} → {positions[j]})"
                        )
                        break

    # --- structure_sequence ---
    sequence = song.get("structure_sequence")
    if not isinstance(sequence, list) or len(sequence) == 0:
        errors.append("structure_sequence est requis et ne peut pas être vide")
    else:
        for sid in sequence:
            if isinstance(sid, str) and not sid.startswith("_comment") and sid not in section_ids:
                errors.append(f"structure_sequence référence un ID inexistant : '{sid}'")

    # --- chords ---
    chords_used = song.get("chords_used", [])
    has_chords_in_sections = any(
        (
            s.get("chord_grid")
            or s.get("summary_progression")
            or any(line.get("chords") for line in s.get("lines", []))
        )
        for s in sections
        if isinstance(s, dict)
    )
    if not chords_used and not has_chords_in_sections:
        errors.append("Aucun accord trouvé (chords_used vide et sections sans accords)")

    # --- performance_progression ---
    for s in sections:
        if not isinstance(s, dict):
            continue
        for entry in s.get("performance_progression", []):
            if not isinstance(entry, dict):
                errors.append(f"Section '{s.get('id')}' : performance_progression doit contenir des objets")
                break
            if "chords" not in entry:
                errors.append(f"Section '{s.get('id')}' : performance_progression[].chords est requis")

    return errors


# ---------------------------------------------------------------------------
# Point d'entrée CLI (usage en ligne de commande)
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_song_json.py data/song_<slug>.json")
        sys.exit(1)
    path = Path(sys.argv[1])
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
    else:
        print(f"OK — JSON valide : {path.name}")


if __name__ == "__main__":
    main()
