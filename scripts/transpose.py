"""
Transposition automatique de tous les accords d'un morceau.
Utilise une gamme chromatique pratique (enharmoniques courants pour la guitare).
"""
import copy
import re

_PRACTICAL = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']

_ENHARMONIC = {
    'Db': 'C#', 'D#': 'Eb', 'Gb': 'F#', 'G#': 'Ab', 'A#': 'Bb',
    'Cb': 'B', 'Fb': 'E', 'E#': 'F', 'B#': 'C',
}

_ROOT_RE = re.compile(r'^([A-G][#b]?)(.*)', re.DOTALL)


def _normalize(root: str) -> str:
    return _ENHARMONIC.get(root, root)


def _shift(root: str, semitones: int) -> str:
    root = _normalize(root)
    if root not in _PRACTICAL:
        return root
    return _PRACTICAL[(_PRACTICAL.index(root) + semitones) % 12]


def _shift_root_only(s: str, semitones: int) -> str:
    m = _ROOT_RE.match(s.strip())
    if not m:
        return s
    return _shift(m.group(1), semitones) + m.group(2)


def transpose_chord(chord: str, semitones: int) -> str:
    """Transpose un accord de `semitones` demi-tons.
    Gère accidentels (Bb, C#, Ab), suffixes (m, maj7, sus4…), accords de basse (G/B).
    Les tokens non reconnus (N.C., -, %) sont retournés tels quels."""
    chord = chord.strip()
    if not chord or semitones == 0:
        return chord
    if '/' in chord:
        parts = chord.split('/', 1)
        return transpose_chord(parts[0], semitones) + '/' + _shift_root_only(parts[1], semitones)
    m = _ROOT_RE.match(chord)
    if not m:
        return chord
    return _shift(m.group(1), semitones) + m.group(2)


def _transpose_tokens(text: str, semitones: int) -> str:
    return ' '.join(transpose_chord(t, semitones) for t in text.split())


def _transpose_chord_grid(chord_grid: str, semitones: int) -> str:
    lines = []
    for line in chord_grid.split('\n'):
        stripped = line.strip()
        if not stripped:
            lines.append(line)
            continue
        tokens = [p.strip() for p in stripped.split('|') if p.strip()]
        if tokens:
            transposed = [transpose_chord(t, semitones) for t in tokens]
            lines.append('| ' + ' | '.join(transposed) + ' |')
        else:
            lines.append(_transpose_tokens(line, semitones))
    return '\n'.join(lines)


def transpose_song(song: dict, semitones: int) -> dict:
    """Transpose tout le morceau de `semitones` demi-tons (−11 à +11).
    Modifie : meta.key, chords_used, lines[].chords[].chord,
              chord_grid, summary_progression, performance_progression[].chords.
    Ne modifie pas meta.capo (ajustement manuel si besoin)."""
    if semitones == 0:
        return copy.deepcopy(song)

    song = copy.deepcopy(song)

    if song.get('meta', {}).get('key'):
        song['meta']['key'] = transpose_chord(song['meta']['key'], semitones)

    song['chords_used'] = [transpose_chord(c, semitones) for c in song.get('chords_used', [])]

    for s in song.get('sections', []):
        for line in s.get('lines', []):
            for entry in line.get('chords', []):
                entry['chord'] = transpose_chord(entry['chord'], semitones)

        if s.get('chord_grid'):
            s['chord_grid'] = _transpose_chord_grid(s['chord_grid'], semitones)

        if s.get('summary_progression'):
            s['summary_progression'] = _transpose_tokens(s['summary_progression'], semitones)

        for perf in s.get('performance_progression', []):
            if isinstance(perf.get('chords'), str):
                perf['chords'] = _transpose_tokens(perf['chords'], semitones)

    return song
