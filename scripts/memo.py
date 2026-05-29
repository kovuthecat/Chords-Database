"""
Fonctions partagées pour la fiche mémo structure guitare et la simplification harmonique.
Importé par generate_docx.py, display_validation.py, validate_harmony.py — aucune dépendance externe.
"""
import copy
import re

# Token d'accord valide : note + qualité + extensions + basse optionnelle
_CHORD_TOKEN_RE = re.compile(
    r'^[A-G][b#]?(?:maj|min|m|M|aug|dim|sus|add)?[0-9]*'
    r'(?:[b#][0-9]+)*(?:sus[0-9]*)?(?:/[A-G][b#]?[0-9]*)?$'
)
# Marqueurs de répétition à supprimer avant extraction : x2, ×3, (x2), (×4)
_REPEAT_RE = re.compile(r'\s*\(?\s*[×x]\s*\d+\s*\)?\s*', re.IGNORECASE)


def _extract_chord_tokens(text: str) -> list:
    """Extrait les tokens d'accords d'une ligne de grille."""
    text = _REPEAT_RE.sub(' ', text)
    return [t for t in re.split(r'[\s|]+', text) if t and _CHORD_TOKEN_RE.match(t)]


def _unique_ordered(chords: list) -> str:
    """Accords sans doublons, dans l'ordre de première apparition."""
    seen, seen_set = [], set()
    for c in chords:
        if c not in seen_set:
            seen.append(c)
            seen_set.add(c)
    return " ".join(seen)


def _extract_progression(section: dict) -> str:
    """Extrait la progression principale d'une section pour la fiche mémo."""
    # 1. Champ explicite (priorité absolue — défini manuellement dans le JSON)
    if section.get("summary_progression"):
        return section["summary_progression"]

    # 2. Depuis chord_grid : première ligne seulement (motif principal)
    chord_grid = section.get("chord_grid")
    if chord_grid:
        first_line = chord_grid.split("\n")[0]
        return _unique_ordered(_extract_chord_tokens(first_line))

    # 3. Depuis les lignes paroles + accords
    lines = section.get("lines", [])
    if lines:
        all_chords = [c["chord"] for line in lines for c in line.get("chords", [])]
        return _unique_ordered(all_chords)

    return ""


def _find_repeat_pattern(seqs: list) -> tuple:
    """
    Détecte si la liste de séquences est la répétition d'un motif plus court.
    Retourne (motif, nombre_de_répétitions). Si aucun motif : (seqs, 1).
    """
    n = len(seqs)
    if n <= 1:
        return seqs, 1
    for period in range(1, n // 2 + 1):
        if n % period == 0:
            pattern = seqs[:period]
            if all(seqs[i] == pattern[i % period] for i in range(n)):
                return pattern, n // period
    return seqs, 1


def _consolidate_identical_lines(lines: list) -> list:
    """Fusionne les entrées consécutives identiques en sommant leurs répétitions."""
    if not lines:
        return lines
    result = [dict(lines[0])]
    for entry in lines[1:]:
        if entry["chords"] == result[-1]["chords"]:
            result[-1]["repeat"] += entry["repeat"]
        else:
            result.append(dict(entry))
    return result


def _extract_performance_lines(section: dict) -> list:
    """
    Extrait les lignes de performance d'une section.
    Retourne une liste de {"chords": str, "repeat": int}.

    Priorité :
    1. performance_progression (JSON explicite)
    2. summary_progression — une ligne, repeat=1
    3. chord_grid — multi-lignes avec détection de répétitions et consolidation
    4. Lignes paroles — détection de motif répété ou fallback _unique_ordered
    """
    # 1. performance_progression (JSON explicite)
    perf = section.get("performance_progression")
    if perf:
        result = []
        for entry in perf:
            chords = entry.get("chords", "")
            if isinstance(chords, list):
                chords = " ".join(chords)
            result.append({"chords": str(chords), "repeat": int(entry.get("repeat", 1))})
        return result or [{"chords": "", "repeat": 1}]

    # 2. summary_progression
    if section.get("summary_progression"):
        return [{"chords": section["summary_progression"], "repeat": 1}]

    # 3. chord_grid (multi-lignes)
    chord_grid = section.get("chord_grid")
    if chord_grid:
        raw_lines = [ln.strip() for ln in chord_grid.split("\n") if ln.strip()]
        entries = []
        for line in raw_lines:
            repeat_m = re.search(r'\(?\s*[×x]\s*(\d+)\s*\)?', line, re.IGNORECASE)
            repeat = int(repeat_m.group(1)) if repeat_m else 1
            tokens = _extract_chord_tokens(line)
            if tokens:
                entries.append({"chords": " ".join(tokens), "repeat": repeat})
        if entries:
            return _consolidate_identical_lines(entries)

    # 4. Lignes paroles — détection de motif répété
    lyric_lines = section.get("lines", [])
    if lyric_lines:
        chord_seqs = []
        for line in lyric_lines:
            chords = [c["chord"] for c in line.get("chords", [])]
            if chords:
                chord_seqs.append(" ".join(chords))
        if chord_seqs:
            pattern, repeat = _find_repeat_pattern(chord_seqs)
            if repeat > 1:
                merged = " ".join(c for seq in pattern for c in seq.split())
                return [{"chords": merged, "repeat": repeat}]
            all_chords = [c for seq in chord_seqs for c in seq.split()]
            return [{"chords": _unique_ordered(all_chords), "repeat": 1}]

    return [{"chords": "", "repeat": 1}]


def _build_rhythm_hint(section: dict) -> str:
    """Construit rhythm_hint depuis section["rhythm"] ou section["rhythm_hint"]."""
    rhythm = section.get("rhythm")
    if rhythm:
        pattern = (rhythm.get("pattern") or "").strip()
        subdivision = (rhythm.get("subdivision") or "").strip()
        if pattern and subdivision:
            return f"{pattern} [{subdivision}]"
        if pattern:
            return pattern
        if subdivision:
            return f"[{subdivision}]"
        return ""
    return section.get("rhythm_hint", "")


def _build_repeat_str(section: dict) -> str:
    """Construit la chaîne de répétition : (x2), (fade), (x4)…"""
    rc = section.get("repeat_count")
    if rc is not None:
        if isinstance(rc, int):
            return f"(x{rc})" if rc > 1 else ""
        return f"({rc})"          # chaîne libre : "fade", "x4", etc.
    repeats = section.get("repeats", 1)
    return f"(x{repeats})" if repeats and repeats > 1 else ""


# ---------------------------------------------------------------------------
# Simplification harmonique
# ---------------------------------------------------------------------------

def _simplify_quality(q: str) -> str:
    """Simplifie la qualité harmonique d'un accord pour un accompagnement guitare simple."""
    if not q:
        return q

    # m7b5, mM7, mmaj7 → m (demi-diminué → mineur)
    if re.match(r'^m(?:7b5|M7|maj7)', q):
        return 'm'

    # m7, m9, m11, m13, madd → m
    if re.match(r'^m(?:[79]|1[13]|add)', q):
        return 'm'

    # maj7, maj9, M7 → '' (accord majeur simple)
    if re.match(r'^[Mm]aj[79]?$|^M7$', q):
        return ''

    # 7sus4, 7sus2, 7sus → '' (accord de base sans suspension)
    if re.match(r'^7sus', q):
        return ''

    # sus4, sus2, sus → '' (accord de base)
    if re.match(r'^sus', q):
        return ''

    # add9, add11, add13 → '' (accord de base)
    if re.match(r'^add', q):
        return ''

    # 7#N, 7bN (altérations) → '7' (garder la dominante, supprimer l'altération)
    if re.match(r'^7[#b]\d', q):
        return '7'

    # 9, 11, 13 (extensions de dominante) → '' (accord de base)
    if re.match(r'^(?:9|11|13)$', q):
        return ''

    # m6 → m
    if re.match(r'^m6$', q):
        return 'm'

    # 6, 6/9 → '' (accord de base)
    if re.match(r'^6(?:/9)?$', q):
        return ''

    return q  # inchangé


def simplify_chord(chord: str) -> tuple:
    """
    Retourne (accord_simplifié, a_changé).
    Supprime extensions et basses slash pour un accompagnement guitare simple.
    """
    original = chord

    # 1. Supprimer la basse slash : C/G → C, Am7/G → Am7
    chord_work = re.sub(r'/[A-G][b#]?[0-9]*$', '', chord)

    # 2. Extraire root + qualité
    m = re.match(r'^([A-G][b#]?)(.*)', chord_work)
    if not m:
        return (original, False)

    root, quality = m.group(1), m.group(2)
    new_quality = _simplify_quality(quality)
    result = root + new_quality

    return (result, result != original)


def _simplification_reason(orig: str) -> str:
    """Retourne une explication courte pour la simplification d'un accord."""
    if '/' in orig:
        return 'basse slash supprimée'
    if re.search(r'm7b5|mM7|mmaj7', orig, re.IGNORECASE):
        return 'demi-diminué → mineur'
    if 'sus' in orig:
        return 'suspension supprimée'
    if 'add' in orig:
        return 'extension add supprimée'
    if re.search(r'maj|M7', orig):
        return 'maj7 supprimé'
    if re.search(r'[#b]\d', orig):
        return 'altération supprimée'
    if re.search(r'm[79]|m1[13]', orig):
        return 'extension 7e supprimée'
    if re.search(r'[79]$|1[13]$', orig):
        return 'extension supprimée'
    if orig.endswith('6'):
        return '6e supprimée'
    return 'extension supprimée'


def build_chord_substitutions(chords: list) -> dict:
    """
    Retourne {accord_original: accord_simplifié} pour les accords simplifiables.
    N'inclut que les accords qui changent réellement.
    """
    result = {}
    for c in chords:
        if isinstance(c, str) and c.startswith('_'):
            continue
        simplified, changed = simplify_chord(c)
        if changed:
            result[c] = simplified
    return result


def is_simplification_relevant(substitutions: dict) -> bool:
    """True si la simplification est assez significative pour être proposée (≥ 2 accords)."""
    return len(substitutions) >= 2


def apply_substitutions_to_song(song: dict, substitutions: dict) -> dict:
    """
    Retourne une copie profonde du song avec les substitutions d'accords appliquées partout :
    chords_used, sections[*].chord_grid, sections[*].lines[*].chords.
    """
    if not substitutions:
        return song

    song = copy.deepcopy(song)

    # chords_used — déduplication en conservant l'ordre
    new_used, seen = [], set()
    for c in song.get("chords_used", []):
        c2 = substitutions.get(c, c)
        if c2 not in seen:
            new_used.append(c2)
            seen.add(c2)
    song["chords_used"] = new_used

    for section in song.get("sections", []):
        # chord_grid : remplacement délimité par \b (word-boundary)
        if section.get("chord_grid"):
            grid = section["chord_grid"]
            for orig, simp in substitutions.items():
                grid = re.sub(r'\b' + re.escape(orig) + r'\b', simp, grid)
            section["chord_grid"] = grid

        # lignes paroles + accords
        for line in section.get("lines", []):
            for entry in line.get("chords", []):
                entry["chord"] = substitutions.get(entry["chord"], entry["chord"])

    return song


def build_memo_lines(song: dict) -> list:
    """
    Retourne la liste ordonnée des lignes de la fiche mémo structure.
    Suit structure_sequence (occurrences multiples incluses).

    Chaque élément :
        {label, progression, repeat, rhythm_hint, mini_tab}
    """
    sections_by_id = {s["id"]: s for s in song.get("sections", [])}
    sequence = [
        x for x in song.get("structure_sequence", [])
        if isinstance(x, str) and not x.startswith("_comment")
    ] or [s["id"] for s in song.get("sections", [])]

    result = []
    for sid in sequence:
        s = sections_by_id.get(sid)
        if not s:
            continue
        perf_lines = _extract_performance_lines(s)
        result.append({
            "label":       s.get("label", s.get("type", sid)),
            "lines":       perf_lines,
            "progression": perf_lines[0]["chords"] if perf_lines else _extract_progression(s),
            "repeat":      _build_repeat_str(s),
            "rhythm_hint": _build_rhythm_hint(s),
            "mini_tab":    s.get("mini_tab_hint", []),
        })
    return result
