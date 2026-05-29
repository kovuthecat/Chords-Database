"""
Fonctions d'édition du JSON chanson.
Appelé par app.py pour les opérations de correction ciblées.
Toutes les fonctions retournent une copie profonde — elles ne mutent jamais le dict original.
"""
import copy
import re
from typing import Optional

from memo import _extract_chord_tokens


# ---------------------------------------------------------------------------
# Remplacement d'accord
# ---------------------------------------------------------------------------

def replace_chord_in_song(
    song: dict,
    old: str,
    new: str,
    section_id: Optional[str] = None,
) -> dict:
    """
    Remplace `old` par `new` dans tout le morceau (ou une section si section_id fourni).
    Champs concernés : chords_used, chord_grid, summary_progression,
    performance_progression[].chords, lines[].chords[].chord.
    Retourne une copie — ne modifie pas l'original.
    """
    old, new = old.strip(), new.strip()
    if not old or not new or old == new:
        return copy.deepcopy(song)

    song = copy.deepcopy(song)

    def _sub(text: str) -> str:
        """Remplace old par new sur des tokens délimités par des espaces/barres."""
        return re.sub(r'(?<![A-Za-z#b])' + re.escape(old) + r'(?![A-Za-z#b0-9])', new, text)

    # chords_used (seulement si remplacement global)
    if section_id is None:
        song["chords_used"] = _replace_in_chords_used(song.get("chords_used", []), old, new)

    for s in song.get("sections", []):
        if section_id and s.get("id") != section_id:
            continue

        if s.get("chord_grid"):
            s["chord_grid"] = _sub(s["chord_grid"])
        if s.get("summary_progression"):
            s["summary_progression"] = _sub(s["summary_progression"])
        for perf in s.get("performance_progression", []):
            if isinstance(perf.get("chords"), str):
                perf["chords"] = _sub(perf["chords"])
        for line in s.get("lines", []):
            for entry in line.get("chords", []):
                if entry.get("chord") == old:
                    entry["chord"] = new

    # Après remplacement sectionnel : recalculer chords_used proprement
    if section_id is not None:
        song["chords_used"] = recalculate_chords_used(song)

    return song


def _replace_in_chords_used(chords_used: list, old: str, new: str) -> list:
    """Remplace old→new dans la liste chords_used en conservant l'ordre et sans doublon."""
    seen, result = set(), []
    for c in chords_used:
        c2 = new if c == old else c
        if c2 not in seen:
            seen.add(c2)
            result.append(c2)
    return result


def recalculate_chords_used(song: dict) -> list:
    """Reconstruit chords_used depuis les sections (ordre d'apparition, sans doublon)."""
    seen, result = set(), []

    def _add(token: str):
        if token and token not in seen:
            seen.add(token)
            result.append(token)

    for s in song.get("sections", []):
        for text in [
            s.get("chord_grid", "") or "",
            s.get("summary_progression", "") or "",
        ] + [p.get("chords", "") or "" for p in s.get("performance_progression", [])]:
            for t in _extract_chord_tokens(text):
                _add(t)
        for line in s.get("lines", []):
            for entry in line.get("chords", []):
                _add(entry.get("chord", ""))

    return result


# ---------------------------------------------------------------------------
# Édition de structure
# ---------------------------------------------------------------------------

def apply_structure_edits(
    song: dict,
    new_sequence: list,
    section_updates: dict,
) -> dict:
    """
    new_sequence    : liste d'IDs de sections dans le nouvel ordre.
    section_updates : {section_id: {"label": str, "type": str, "repeats": int}}
    Les _comment du début de la séquence originale sont conservés.
    """
    song = copy.deepcopy(song)

    # Mettre à jour les définitions de sections
    for s in song.get("sections", []):
        sid = s.get("id")
        upd = section_updates.get(sid, {})
        if upd.get("label"):
            s["label"] = upd["label"].strip()
        if upd.get("type"):
            s["type"] = upd["type"].strip()
        if "repeats" in upd:
            try:
                s["repeats"] = max(1, int(upd["repeats"]))
            except (ValueError, TypeError):
                pass

    # Reconstruire structure_sequence (conserver les _comment initiaux)
    old_seq = song.get("structure_sequence", [])
    comments = [x for x in old_seq if isinstance(x, str) and x.startswith("_comment")]
    song["structure_sequence"] = comments + [sid for sid in new_sequence if sid]

    return song


def add_new_section(
    song: dict,
    label: str,
    section_type: str,
    chord_grid: Optional[str] = None,
    append_to_sequence: bool = True,
) -> dict:
    """
    Crée une nouvelle section dans sections[] et l'ajoute en fin de structure_sequence.
    L'ID est auto-généré : {type}_{n+1} où n est le nombre de sections de ce type.
    """
    song = copy.deepcopy(song)
    label = label.strip()
    section_type = section_type.strip()

    # Compter les sections existantes de ce type pour générer un ID unique
    existing_ids = {s.get("id", "") for s in song.get("sections", [])}
    n = sum(1 for sid in existing_ids if sid.startswith(section_type + "_"))
    new_id = f"{section_type}_{n + 1}"
    # Éviter les collisions
    while new_id in existing_ids:
        n += 1
        new_id = f"{section_type}_{n + 1}"

    new_section: dict = {
        "id":              new_id,
        "type":            section_type,
        "label":           label,
        "is_instrumental": bool(chord_grid),
        "repeats":         1,
        "lines":           [],
    }
    if chord_grid:
        new_section["chord_grid"] = chord_grid.strip()

    song.setdefault("sections", []).append(new_section)

    if append_to_sequence:
        song.setdefault("structure_sequence", []).append(new_id)

    return song


# ---------------------------------------------------------------------------
# Édition du rythme
# ---------------------------------------------------------------------------

def update_section_rhythm(
    song: dict,
    section_id: str,
    pattern: str,
    feel: str,
) -> dict:
    """
    Met à jour rhythm.pattern et rhythm.feel d'une section.
    Si les deux champs sont vides, supprime la clé rhythm.
    """
    song = copy.deepcopy(song)
    pattern, feel = pattern.strip(), feel.strip()

    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        if pattern or feel:
            s.setdefault("rhythm", {})
            s["rhythm"]["pattern"] = pattern
            s["rhythm"]["feel"] = feel
        else:
            s.pop("rhythm", None)
        break

    return song


def apply_all_rhythm_edits(song: dict, edits: dict) -> dict:
    """
    edits : {section_id: {"pattern": str, "feel": str}}
    Applique update_section_rhythm pour chaque section dans edits.
    """
    for section_id, fields in edits.items():
        song = update_section_rhythm(
            song, section_id,
            fields.get("pattern", ""),
            fields.get("feel", ""),
        )
    return song


# ---------------------------------------------------------------------------
# Édition ciblée d'accords (position précise dans lines[].chords[])
# ---------------------------------------------------------------------------

def delete_chord_at(
    song: dict,
    section_id: str,
    line_index: int,
    chord_index: int,
) -> dict:
    """Supprime l'accord à chord_index dans lines[line_index] de section_id."""
    song = copy.deepcopy(song)
    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        lines = s.get("lines", [])
        if 0 <= line_index < len(lines):
            chords = lines[line_index].get("chords", [])
            if 0 <= chord_index < len(chords):
                chords.pop(chord_index)
        break
    song["chords_used"] = recalculate_chords_used(song)
    return song


def update_chord_at(
    song: dict,
    section_id: str,
    line_index: int,
    chord_index: int,
    new_chord: str,
) -> dict:
    """Modifie un accord spécifique sans toucher aux autres occurrences du même accord."""
    song = copy.deepcopy(song)
    new_chord = new_chord.strip()
    if not new_chord:
        return song
    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        lines = s.get("lines", [])
        if 0 <= line_index < len(lines):
            chords = lines[line_index].get("chords", [])
            if 0 <= chord_index < len(chords):
                chords[chord_index]["chord"] = new_chord
        break
    song["chords_used"] = recalculate_chords_used(song)
    return song


def insert_chord_at(
    song: dict,
    section_id: str,
    line_index: int,
    chord: str,
    position: int,
) -> dict:
    """Insère un accord à la position (offset caractère) donnée dans lines[line_index].
    Les accords existants sont triés par position après insertion."""
    song = copy.deepcopy(song)
    chord = chord.strip()
    if not chord:
        return song
    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        lines = s.get("lines", [])
        if 0 <= line_index < len(lines):
            chords = lines[line_index].setdefault("chords", [])
            chords.append({"chord": chord, "position": position})
            chords.sort(key=lambda c: c.get("position", 0))
        break
    song["chords_used"] = recalculate_chords_used(song)
    return song


# ---------------------------------------------------------------------------
# Édition ciblée d'accords dans les sections instrumentales
# ---------------------------------------------------------------------------

def _cg_lines(chord_grid: str) -> list[str]:
    """Retourne toutes les lignes d'un chord_grid (conserve les vides pour rebuildage)."""
    return chord_grid.split("\n")


def _parse_cg_line(line: str) -> list[str]:
    """Parse '| Am | C | G |' → ['Am', 'C', 'G']."""
    return [p.strip() for p in line.split("|") if p.strip()]


def _build_cg_line(chords: list[str]) -> str:
    return "| " + " | ".join(chords) + " |" if chords else ""


def update_instr_chord(
    song: dict,
    section_id: str,
    instr_type: str,
    chord_index: int,
    new_chord: str,
    ppi: int = 0,
    li: int = 0,
) -> dict:
    """Modifie un accord dans performance_progression ('pp'), chord_grid ('cg') ou
    summary_progression ('sp') d'une section instrumentale."""
    song = copy.deepcopy(song)
    new_chord = new_chord.strip()
    if not new_chord:
        return song
    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        if instr_type == "pp":
            pp = s.get("performance_progression", [])
            if 0 <= ppi < len(pp):
                tokens = pp[ppi]["chords"].split()
                if 0 <= chord_index < len(tokens):
                    tokens[chord_index] = new_chord
                    pp[ppi]["chords"] = " ".join(tokens)
        elif instr_type == "cg":
            lines = _cg_lines(s.get("chord_grid", ""))
            if 0 <= li < len(lines):
                chords = _parse_cg_line(lines[li])
                if 0 <= chord_index < len(chords):
                    chords[chord_index] = new_chord
                    lines[li] = _build_cg_line(chords)
                    s["chord_grid"] = "\n".join(lines)
        elif instr_type == "sp":
            tokens = s.get("summary_progression", "").split()
            if 0 <= chord_index < len(tokens):
                tokens[chord_index] = new_chord
                s["summary_progression"] = " ".join(tokens)
        break
    song["chords_used"] = recalculate_chords_used(song)
    return song


def delete_instr_chord(
    song: dict,
    section_id: str,
    instr_type: str,
    chord_index: int,
    ppi: int = 0,
    li: int = 0,
) -> dict:
    """Supprime un accord dans performance_progression, chord_grid ou summary_progression."""
    song = copy.deepcopy(song)
    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        if instr_type == "pp":
            pp = s.get("performance_progression", [])
            if 0 <= ppi < len(pp):
                tokens = pp[ppi]["chords"].split()
                if 0 <= chord_index < len(tokens):
                    tokens.pop(chord_index)
                    pp[ppi]["chords"] = " ".join(tokens)
        elif instr_type == "cg":
            lines = _cg_lines(s.get("chord_grid", ""))
            if 0 <= li < len(lines):
                chords = _parse_cg_line(lines[li])
                if 0 <= chord_index < len(chords):
                    chords.pop(chord_index)
                    lines[li] = _build_cg_line(chords)
                    s["chord_grid"] = "\n".join(lines)
        elif instr_type == "sp":
            tokens = s.get("summary_progression", "").split()
            if 0 <= chord_index < len(tokens):
                tokens.pop(chord_index)
                s["summary_progression"] = " ".join(tokens)
        break
    song["chords_used"] = recalculate_chords_used(song)
    return song


def insert_instr_chord(
    song: dict,
    section_id: str,
    instr_type: str,
    insert_at: int,
    chord: str,
    ppi: int = 0,
    li: int = 0,
) -> dict:
    """Insère un accord à l'index insert_at dans performance_progression ('pp'),
    chord_grid ('cg') ou summary_progression ('sp') d'une section instrumentale."""
    song = copy.deepcopy(song)
    chord = chord.strip()
    if not chord:
        return song
    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        if instr_type == "pp":
            pp = s.get("performance_progression", [])
            if 0 <= ppi < len(pp):
                tokens = pp[ppi]["chords"].split()
                tokens.insert(max(0, insert_at), chord)
                pp[ppi]["chords"] = " ".join(tokens)
        elif instr_type == "cg":
            lines = _cg_lines(s.get("chord_grid", ""))
            if 0 <= li < len(lines):
                chords = _parse_cg_line(lines[li])
                chords.insert(max(0, insert_at), chord)
                lines[li] = _build_cg_line(chords)
                s["chord_grid"] = "\n".join(lines)
        elif instr_type == "sp":
            tokens = s.get("summary_progression", "").split()
            tokens.insert(max(0, insert_at), chord)
            s["summary_progression"] = " ".join(tokens)
        break
    song["chords_used"] = recalculate_chords_used(song)
    return song


# ---------------------------------------------------------------------------
# Déplacement de position d'accord (dans lines[].chords[])
# ---------------------------------------------------------------------------

def move_chord_at(
    song: dict,
    section_id: str,
    line_index: int,
    chord_index: int,
    delta: int,
) -> dict:
    """Déplace un accord de |delta| caractères vers la gauche (delta<0) ou la droite (delta>0).
    La position est ramenée à 0 minimum. Les accords sont re-triés par position après déplacement."""
    song = copy.deepcopy(song)
    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        lines = s.get("lines", [])
        if 0 <= line_index < len(lines):
            chords = lines[line_index].get("chords", [])
            if 0 <= chord_index < len(chords):
                chords[chord_index]["position"] = max(0, chords[chord_index]["position"] + delta)
                lines[line_index]["chords"] = sorted(chords, key=lambda c: c.get("position", 0))
        break
    return song


def set_chord_position(
    song: dict,
    section_id: str,
    line_index: int,
    chord_index: int,
    position: int,
) -> dict:
    """Fixe la position d'un accord à un offset exact (en caractères, minimum 0).
    Les accords sont re-triés par position après modification."""
    song = copy.deepcopy(song)
    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        lines = s.get("lines", [])
        if 0 <= line_index < len(lines):
            chords = lines[line_index].get("chords", [])
            if 0 <= chord_index < len(chords):
                chords[chord_index]["position"] = max(0, position)
                lines[line_index]["chords"] = sorted(chords, key=lambda c: c.get("position", 0))
        break
    return song


# ---------------------------------------------------------------------------
# Édition inline des paroles
# ---------------------------------------------------------------------------

def update_lyrics_at(
    song: dict,
    section_id: str,
    line_index: int,
    new_lyrics: str,
) -> dict:
    """Modifie le texte de paroles d'une ligne sans toucher aux accords ni à leurs positions."""
    song = copy.deepcopy(song)
    for s in song.get("sections", []):
        if s.get("id") != section_id:
            continue
        lines = s.get("lines", [])
        if 0 <= line_index < len(lines):
            lines[line_index]["lyrics"] = new_lyrics
        break
    return song
