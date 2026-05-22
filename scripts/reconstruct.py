"""
Reconstruit la structure unifiée d'un fichier song JSON à partir de plusieurs sources.

Actions :
  - Fusionne les sections de toutes les sources en un seul jeu de sections
  - Calcule source_agreement et chord_agreement par section
  - Détecte les divergences (capo, tonalité, accords, sections manquantes)
  - Met à jour les scores de confiance globaux
  - Enregistre _collection_status = "reconstructed"

Usage : python scripts/reconstruct.py data/song_<slug>.json
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
# Utilitaires section
# ---------------------------------------------------------------------------

def base_id(section_id: str) -> str:
    return re.sub(r'_s\d+$', '', section_id)


def source_index(section_id: str) -> int:
    m = re.search(r'_s(\d+)$', section_id)
    return int(m.group(1)) if m else 1


def extract_chord_set(section: dict) -> set:
    chords = set()
    if section.get("chord_grid"):
        for token in re.sub(r'[|]', ' ', section["chord_grid"]).split():
            if re.match(r'^[A-G][b#]?', token) and len(token) <= 8:
                chords.add(token.strip("()[]"))
    for line in section.get("lines", []):
        for c in line.get("chords", []):
            chords.add(c["chord"])
    return chords


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


# ---------------------------------------------------------------------------
# Fusion des sources
# ---------------------------------------------------------------------------

def group_by_base_id(sections: list) -> dict[str, list]:
    """Groupe les sections par base_id, en conservant l'ordre de première apparition."""
    groups: dict[str, list] = {}
    for s in sections:
        bid = base_id(s["id"])
        groups.setdefault(bid, []).append(s)
    return groups


def unify_section_group(bid: str, group: list, n_sources: int) -> dict:
    """
    Fusionne un groupe de sections (une par source) en une section unifiée.
    La section primaire (source 1, sans suffixe) sert de base.
    """
    primary = group[0]

    # Accord entre sources sur les accords
    chord_sets = [extract_chord_set(s) for s in group]
    if len(chord_sets) > 1:
        pairwise = []
        for i in range(len(chord_sets)):
            for j in range(i + 1, len(chord_sets)):
                pairwise.append(jaccard(chord_sets[i], chord_sets[j]))
        chord_agreement = sum(pairwise) / len(pairwise)
    else:
        chord_agreement = 1.0

    source_agreement = len(group) / n_sources
    base_conf = primary.get("confidence", 0.75)
    confidence = round(base_conf * 0.4 + source_agreement * 0.4 + chord_agreement * 0.2, 2)

    return {
        **primary,
        "id": bid,
        "source_agreement": round(source_agreement, 2),
        "chord_agreement": round(chord_agreement, 2),
        "confidence": confidence,
        "n_sources": len(group),
    }


# ---------------------------------------------------------------------------
# Détection des divergences
# ---------------------------------------------------------------------------

def detect_divergences(song: dict, groups: dict[str, list], n_sources: int) -> list[dict]:
    warnings = []
    sources = song.get("sources", [])

    # Divergence de capo
    capos = [s.get("capo", 0) for s in sources if s.get("capo") is not None]
    if len(set(capos)) > 1:
        vals = ", ".join(str(c) for c in capos)
        warnings.append({
            "severity": "high",
            "section": None,
            "message": f"Capo divergent entre sources : {vals} — choisir avant validation",
        })

    # Divergence de tonalité
    keys = [s.get("key") for s in sources if s.get("key")]
    if len(set(keys)) > 1:
        vals = ", ".join(str(k) for k in keys)
        warnings.append({
            "severity": "high",
            "section": None,
            "message": f"Tonalité divergente entre sources : {vals}",
        })

    # Sections présentes dans une seule source
    for bid, group in groups.items():
        if len(group) < n_sources:
            missing_in = n_sources - len(group)
            section = group[0]
            label = section.get("label", bid)
            warnings.append({
                "severity": "low",
                "section": bid,
                "message": f"Section '{label}' absente de {missing_in}/{n_sources} source(s)",
            })

    # Faible accord d'accords entre sources
    for bid, group in groups.items():
        if len(group) < 2:
            continue
        chord_sets = [extract_chord_set(s) for s in group]
        pairwise = [
            jaccard(chord_sets[i], chord_sets[j])
            for i in range(len(chord_sets))
            for j in range(i + 1, len(chord_sets))
        ]
        avg = sum(pairwise) / len(pairwise) if pairwise else 1.0
        if avg < 0.60:
            section = group[0]
            label = section.get("label", bid)
            source_chords = [
                f"s{source_index(g['id'])}: {' '.join(sorted(extract_chord_set(g)))}"
                for g in group
            ]
            warnings.append({
                "severity": "medium",
                "section": bid,
                "message": (
                    f"Accords divergents dans '{label}' (accord={avg:.0%}) — "
                    + " | ".join(source_chords)
                ),
            })

    return warnings


# ---------------------------------------------------------------------------
# Calcul des scores globaux
# ---------------------------------------------------------------------------

def compute_global_confidence(unified_sections: list, n_sources: int) -> dict:
    if not unified_sections:
        return {"overall": 0.0, "structure": 0.0, "chords": 0.0,
                "capo": 0.0, "instrumental_sections": 0.0, "lyric_alignment": 0.0}

    structure = sum(s["source_agreement"] for s in unified_sections) / len(unified_sections)
    chords = sum(s["chord_agreement"] for s in unified_sections) / len(unified_sections)

    instr_sections = [s for s in unified_sections if s.get("is_instrumental")]
    instr_score = (
        sum(s["source_agreement"] for s in instr_sections) / len(instr_sections)
        if instr_sections else structure
    )

    lyric_sections = [s for s in unified_sections if not s.get("is_instrumental")]
    lyric_score = (
        sum(s["chord_agreement"] for s in lyric_sections) / len(lyric_sections)
        if lyric_sections else chords
    )

    # capo : calculé plus tard par validate_harmony
    capo = 0.0

    overall = round(structure * 0.35 + chords * 0.35 + instr_score * 0.15 + lyric_score * 0.15, 2)

    return {
        "overall": overall,
        "structure": round(structure, 2),
        "chords": round(chords, 2),
        "capo": capo,
        "instrumental_sections": round(instr_score, 2),
        "lyric_alignment": round(lyric_score, 2),
    }


# ---------------------------------------------------------------------------
# Reconstruction
# ---------------------------------------------------------------------------

def reconstruct(json_path: str):
    song = load_song(json_path)
    sources = song.get("sources", [])
    n_sources = len(sources)

    if n_sources == 0:
        print("Aucune source collectée. Lance d'abord collect.py --ingest.")
        sys.exit(1)

    if n_sources == 1:
        print("  ⚠  Une seule source — reconstruction partielle (confiance limitée).")

    # Grouper toutes les sections par base_id
    all_sections = song.get("sections", [])
    groups = group_by_base_id(all_sections)

    # Créer les sections unifiées (ordre de première apparition = ordre source 1)
    unified_sections = [
        unify_section_group(bid, group, n_sources)
        for bid, group in groups.items()
    ]

    # Structure sequence : reprend la sequence source 1, remplace les IDs suffixés
    original_seq = song.get("structure_sequence", [])
    sequence_base_ids = []
    seen_in_seq = set()
    for sid in original_seq:
        bid = base_id(sid)
        if bid not in seen_in_seq:
            sequence_base_ids.append(bid)
            seen_in_seq.add(bid)

    # Vérifier que la sequence contient toutes les sections
    seq_set = set(sequence_base_ids)
    for bid in groups:
        if bid not in seq_set:
            sequence_base_ids.append(bid)

    # Détecter les divergences
    new_warnings = detect_divergences(song, groups, n_sources)

    # Conserver les warnings précédents + ajouter les nouveaux
    existing = song.get("warnings", [])
    merged_warnings = existing + [w for w in new_warnings if w not in existing]

    # Calcul des scores globaux
    global_conf = compute_global_confidence(unified_sections, n_sources)

    # Mise à jour du JSON
    song["sections"] = unified_sections
    song["structure_sequence"] = sequence_base_ids
    song["warnings"] = merged_warnings
    song["confidence"] = {**song.get("confidence", {}), **global_conf}
    song["_collection_status"] = f"reconstructed ({n_sources} source(s))"

    save_song(song, json_path)

    # Résumé
    print(f"\n  ✓ Reconstruction terminée : {json_path}")
    print(f"  Sections unifiées    : {len(unified_sections)}")
    print(f"  Structure sequence   : {' → '.join(sequence_base_ids)}")
    print(f"  Divergences détectées : {len(new_warnings)}")

    for w in new_warnings:
        sev = {"high": "⚠ HAUT  ", "medium": "⚠ MOYEN ", "low": "ℹ FAIBLE"}.get(w["severity"], "ℹ ")
        section_tag = f"[{w['section']}] " if w.get("section") else ""
        print(f"    {sev} {section_tag}{w['message']}")

    print(f"  Score global (provisoire) : {int(global_conf['overall'] * 100)}%")
    print()
    print("  → Étape suivante :")
    print(f"    python scripts/validate_harmony.py {json_path}")
    print()


def main():
    _ensure_utf8()
    if len(sys.argv) < 2:
        print("Usage : python scripts/reconstruct.py data/song_<slug>.json")
        sys.exit(1)
    reconstruct(sys.argv[1])


if __name__ == "__main__":
    main()
