"""
Validation harmonique d'un fichier song JSON.

Actions :
  - Détecte la tonalité depuis l'ensemble des accords si non définie
  - Identifie les accords hors gamme diatonique
  - Vérifie la cohérence capo ↔ tonalité
  - Met à jour les scores de confiance (chords, capo, overall)
  - Ajoute des warnings pour les éléments suspects
  - Enregistre _collection_status = "validated"

Usage : python scripts/validate_harmony.py data/song_<slug>.json
"""

import io
import json
import re
import sys
from pathlib import Path


def _ensure_utf8():
    if hasattr(sys.stdout, "buffer") and getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


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


# ---------------------------------------------------------------------------
# Théorie musicale
# ---------------------------------------------------------------------------

# Représentation des notes en demi-tons (C=0)
NOTE_TO_SEMI = {
    'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3,
    'E': 4, 'F': 5, 'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8,
    'A': 9, 'A#': 10, 'Bb': 10, 'B': 11,
}

# Noms préférés des notes (éviter les doubles bémols/dièses)
SEMI_TO_NOTE = {
    0: 'C', 1: 'C#', 2: 'D', 3: 'Eb', 4: 'E', 5: 'F',
    6: 'F#', 7: 'G', 8: 'Ab', 9: 'A', 10: 'Bb', 11: 'B',
}

# Intervalles diatoniques depuis la tonique (demi-tons)
MAJOR_SCALE = [0, 2, 4, 5, 7, 9, 11]
MINOR_SCALE = [0, 2, 3, 5, 7, 8, 10]    # mineur naturel
HARMONIC_MINOR_EXTRA = [0, 2, 3, 5, 7, 8, 11]  # mineur harmonique

# Qualités diatoniques pour gamme majeure (par degré I..VII)
MAJOR_QUALITIES = ['maj', 'min', 'min', 'maj', 'maj', 'min', 'dim']
# Qualités pour mineur naturel (par degré i..VII)
MINOR_QUALITIES = ['min', 'dim', 'maj', 'min', 'min', 'maj', 'maj']

# Regex pour parser un accord
CHORD_PARSE_RE = re.compile(
    r'^(?P<root>[A-G][b#]?)'
    r'(?P<quality>m(?:aj)?|min|aug|dim|sus\d*)?'
    r'(?P<ext>\d+)?'
    r'(?:add\d+)?'
    r'(?:/[A-G][b#]?)?$'
)


def parse_chord(chord_str: str) -> tuple[int, str] | None:
    """
    Parse un accord et retourne (root_semitone, quality).
    quality : 'maj', 'min', 'dim', 'aug', 'sus'.
    Retourne None si non reconnu.
    """
    m = CHORD_PARSE_RE.match(chord_str.strip("()[]"))
    if not m:
        return None
    root = m.group("root")
    raw_q = m.group("quality") or ""

    root_semi = NOTE_TO_SEMI.get(root)
    if root_semi is None:
        return None

    if "dim" in raw_q:
        quality = "dim"
    elif "aug" in raw_q:
        quality = "aug"
    elif "sus" in raw_q:
        quality = "sus"
    elif raw_q in ("m", "min"):
        quality = "min"
    elif raw_q == "maj":
        quality = "maj"
    elif raw_q == "":
        quality = "maj"
    else:
        quality = "maj"

    return (root_semi, quality)


def diatonic_notes(root_semi: int, mode: str) -> set[int]:
    """Retourne l'ensemble des notes diatoniques (en demi-tons) pour une tonalité."""
    scale = MAJOR_SCALE if mode == "major" else MINOR_SCALE
    notes = {(root_semi + interval) % 12 for interval in scale}
    if mode == "minor":
        # Ajouter la septième de la gamme harmonique (sensible)
        notes.add((root_semi + 11) % 12)
    return notes


def expected_quality(degree_index: int, mode: str) -> str:
    """Qualité attendue pour le degré diatonique à l'index donné (0=I, 1=II, etc.)."""
    qualities = MAJOR_QUALITIES if mode == "major" else MINOR_QUALITIES
    if 0 <= degree_index < len(qualities):
        return qualities[degree_index]
    return "maj"


# ---------------------------------------------------------------------------
# Détection de tonalité
# ---------------------------------------------------------------------------

def detect_key(chords: list[str]) -> tuple[str, str, float]:
    """
    Détecte la tonalité la plus probable depuis une liste d'accords.
    Retourne (root_name, mode, score).
    """
    parsed = [parse_chord(c) for c in chords if parse_chord(c) is not None]
    if not parsed:
        return ("C", "major", 0.0)

    best_key = "C"
    best_mode = "major"
    best_score = -1.0

    for root_semi in range(12):
        for mode in ("major", "minor"):
            diatonic = diatonic_notes(root_semi, mode)
            # Score = fraction des accords dont la racine est diatonique
            # Bonus si la qualité correspond aussi
            score = 0.0
            for chord_semi, chord_quality in parsed:
                if chord_semi in diatonic:
                    degree_idx = list(
                        MAJOR_SCALE if mode == "major" else MINOR_SCALE
                    ).index(
                        (chord_semi - root_semi) % 12
                    ) if (chord_semi - root_semi) % 12 in (MAJOR_SCALE if mode == "major" else MINOR_SCALE) else -1

                    if degree_idx >= 0:
                        exp_q = expected_quality(degree_idx, mode)
                        if exp_q == chord_quality:
                            score += 1.0
                        else:
                            score += 0.7  # racine ok, qualité différente
                    else:
                        score += 0.5  # racine diatonique via harmonique

            score = score / len(parsed)
            if score > best_score:
                best_score = score
                best_key = SEMI_TO_NOTE[root_semi]
                best_mode = mode

    return (best_key, best_mode, round(best_score, 2))


# ---------------------------------------------------------------------------
# Vérification harmonique
# ---------------------------------------------------------------------------

def is_secondary_dominant(chord_semi: int, chord_quality: str, root_semi: int, mode: str) -> bool:
    """
    Vérifie si l'accord peut être une dominante secondaire (V/X).
    Une dominante secondaire est un accord majeur ou de dominante (7)
    situé une quinte au-dessus d'un accord diatonique.
    """
    if chord_quality not in ("maj",):
        return False
    diatonic = diatonic_notes(root_semi, mode)
    # La résolution d'une dominante secondaire = chord_semi + 5 (quinte en dessous)
    resolution = (chord_semi + 5) % 12
    return resolution in diatonic


def check_chord_harmony(
    chord_str: str, root_semi: int, mode: str
) -> dict | None:
    """
    Retourne un dict de warning si l'accord est suspect, None sinon.
    """
    parsed = parse_chord(chord_str)
    if not parsed:
        return None

    chord_semi, chord_quality = parsed
    diatonic = diatonic_notes(root_semi, mode)

    if chord_semi in diatonic:
        return None  # diatonique, OK

    # Hors gamme : vérifier si dominante secondaire
    if is_secondary_dominant(chord_semi, chord_quality, root_semi, mode):
        return None  # dominante secondaire, acceptable

    return {
        "chord": chord_str,
        "reason": "hors gamme diatonique",
    }


def collect_all_chords(song: dict) -> list[str]:
    """Collecte tous les accords uniques du morceau."""
    chords = set(song.get("chords_used", []))
    for section in song.get("sections", []):
        if section.get("chord_grid"):
            for token in re.sub(r'[|]', ' ', section["chord_grid"]).split():
                if re.match(r'^[A-G][b#]?', token):
                    chords.add(token.strip("()[]"))
        for line in section.get("lines", []):
            for c in line.get("chords", []):
                chords.add(c["chord"])
    return [c for c in chords if parse_chord(c) is not None]


# ---------------------------------------------------------------------------
# Validation capo ↔ tonalité
# ---------------------------------------------------------------------------

def validate_capo(sources: list, meta_key: str | None, meta_capo: int) -> dict | None:
    """
    Vérifie la cohérence capo ↔ tonalité entre les sources.
    Si source A dit key=G capo=0 et source B dit key=A capo=0,
    elles ne sont pas cohérentes.
    """
    if not meta_key:
        return None

    meta_root = NOTE_TO_SEMI.get(re.match(r'[A-G][b#]?', meta_key).group() if meta_key else "C", 0)

    for source in sources:
        src_key = source.get("key")
        src_capo = source.get("capo", 0) or 0
        if not src_key:
            continue
        src_root = NOTE_TO_SEMI.get(re.match(r'[A-G][b#]?', src_key).group() if src_key else "C", 0)
        sounded_root = (src_root + src_capo) % 12
        expected_root = (meta_root + meta_capo) % 12

        # Tolérer la relation relative majeur/mineur (3 demi-tons d'écart)
        relative_root = (expected_root + 3) % 12
        if sounded_root != expected_root and sounded_root != relative_root:
            return {
                "severity": "medium",
                "section": None,
                "message": (
                    f"Incohérence capo/tonalité pour '{source['name']}' : "
                    f"key={src_key} capo={src_capo} → sonne {SEMI_TO_NOTE[sounded_root]}, "
                    f"attendu {SEMI_TO_NOTE[expected_root]}"
                ),
            }
    return None


# ---------------------------------------------------------------------------
# Point d'entrée
# ---------------------------------------------------------------------------

def validate_harmony(json_path: str):
    song = load_song(json_path)
    meta = song["meta"]
    sources = song.get("sources", [])
    warnings = song.get("warnings", [])

    # 1. Collecter tous les accords
    all_chords = collect_all_chords(song)
    if not all_chords:
        print("  ⚠  Aucun accord trouvé dans le fichier. Reconstruction requise d'abord.")
        sys.exit(1)

    # 2. Normaliser et détecter la tonalité
    raw_key = meta.get("key")
    key_mode = meta.get("key_mode")

    # Extraire root et mode depuis la clé brute (ex: "Am" → root="A", mode="minor")
    if raw_key:
        m_key = re.match(r'([A-G][b#]?)(m(?:in)?)?', raw_key, re.IGNORECASE)
        if m_key:
            key = m_key.group(1)
            if not key_mode:
                key_mode = "minor" if m_key.group(2) else "major"
        else:
            key = raw_key
        meta["key"] = key
        meta["key_mode"] = key_mode
    else:
        key = None

    if not key:
        key, key_mode, key_score = detect_key(all_chords)
        meta["key"] = key
        meta["key_mode"] = key_mode
        print(f"  Tonalité détectée : {key} {'majeur' if key_mode == 'major' else 'mineur'} (score={key_score:.0%})")
        if key_score < 0.65:
            warnings.append({
                "severity": "medium",
                "section": None,
                "message": f"Tonalité détectée avec faible confiance ({key_score:.0%}) : {key} {key_mode}. Vérifier manuellement.",
            })
    else:
        # Recalculer le score de cohérence pour la tonalité déclarée
        root_semi = NOTE_TO_SEMI.get(key, 0)
        diatonic = diatonic_notes(root_semi, key_mode or "major")
        diatonic_count = sum(
            1 for c in all_chords
            if (parsed := parse_chord(c)) and parsed[0] in diatonic
        )
        key_score = diatonic_count / len(all_chords) if all_chords else 0.0
        print(f"  Tonalité déclarée : {key} {'majeur' if key_mode == 'major' else 'mineur'} (cohérence={key_score:.0%})")

    # 3. Identifier accords hors gamme
    root_semi = NOTE_TO_SEMI.get(key, 0)
    suspicious = []
    for chord in all_chords:
        w = check_chord_harmony(chord, root_semi, key_mode or "major")
        if w:
            suspicious.append(w)

    if suspicious:
        chord_list = ", ".join(w["chord"] for w in suspicious)
        warnings.append({
            "severity": "low",
            "section": None,
            "message": f"Accords hors gamme ({key} {key_mode}) : {chord_list} — vérifier (peut être normal : emprunt modal, dominante secondaire)",
        })

    # 4. Valider cohérence capo ↔ tonalité
    capo = meta.get("capo", 0) or 0
    capo_warning = validate_capo(sources, key, capo)
    if capo_warning:
        warnings.append(capo_warning)

    # 5. Mettre à jour les scores de confiance
    n_diatonic = len(all_chords) - len(suspicious)
    chord_score = n_diatonic / len(all_chords) if all_chords else 0.0

    # Capo score : 1.0 si pas de divergence capo, 0.5 si warning
    capo_score = 0.5 if capo_warning else 1.0
    if not sources or all(s.get("capo") == capo for s in sources):
        capo_score = 1.0

    conf = song.get("confidence", {})
    conf["chords"] = round(max(conf.get("chords", chord_score), chord_score), 2)
    conf["capo"] = round(capo_score, 2)

    # Recalculer overall
    structure = conf.get("structure", 0.5)
    chords = conf["chords"]
    instr = conf.get("instrumental_sections", structure)
    lyric = conf.get("lyric_alignment", chords)
    conf["overall"] = round(
        structure * 0.30 + chords * 0.30 + capo_score * 0.15 + instr * 0.12 + lyric * 0.13, 2
    )

    song["confidence"] = conf
    song["warnings"] = warnings
    song["_collection_status"] = "validated"

    save_song(song, json_path)

    # Résumé
    key_label = "majeur" if key_mode == "major" else "mineur"
    print(f"\n  ✓ Validation harmonique terminée : {json_path}")
    print(f"  Tonalité          : {key} {key_label}")
    print(f"  Capo              : {capo if capo else 'aucun'}")
    print(f"  Accords analysés  : {len(all_chords)}")
    print(f"  Accords suspects  : {len(suspicious)} ({', '.join(w['chord'] for w in suspicious) or 'aucun'})")
    print(f"  Score harmonique  : {int(chord_score * 100)}%")
    print(f"  Score capo        : {int(capo_score * 100)}%")
    print(f"  Score global      : {int(conf['overall'] * 100)}%")
    if warnings:
        print(f"  Avertissements    : {len(warnings)}")
    print()
    print("  → Valider avant génération :")
    print(f"    python scripts/display_validation.py {json_path}")
    print()


def main():
    _ensure_utf8()
    if len(sys.argv) < 2:
        print("Usage : python scripts/validate_harmony.py data/song_<slug>.json")
        sys.exit(1)
    validate_harmony(sys.argv[1])


if __name__ == "__main__":
    main()
