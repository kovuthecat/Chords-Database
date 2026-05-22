"""
audio_compare.py — Comparaison audio vs JSON chords (orientatif, non bloquant).

Usage:
    python scripts/audio_compare.py data/song_<slug>.json audio/<file>.<ext>

Dépendances:
    pip install librosa soundfile

Sorties:
    output/audio_report_<slug>.md

Rapport orientatif uniquement. La validation humaine reste obligatoire avant DOCX.
"""

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path
from datetime import datetime

_NOTES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
_ENHARMONIC = {'Db': 'C#', 'Eb': 'D#', 'Gb': 'F#', 'Ab': 'G#', 'Bb': 'A#'}
_FLAT_DISPLAY = {'C#': 'Db', 'D#': 'Eb', 'G#': 'Ab', 'A#': 'Bb'}


def _normalize_note(note: str) -> str:
    return _ENHARMONIC.get(note, note)


def _display_note(note: str, mode: str) -> str:
    """Affiche les bémols pour les tonalités mineures (plus naturel en pop/rock)."""
    if mode == 'minor' and note in _FLAT_DISPLAY:
        return _FLAT_DISPLAY[note]
    return note


def _transpose_chord(chord: str, semitones: int) -> str:
    """Transpose un accord (triade) de n demi-tons. Am + 1 → A#m."""
    m = re.match(r'^([A-G][#b]?)(m?)$', chord)
    if not m or semitones == 0:
        return chord
    root = _normalize_note(m.group(1))
    quality = m.group(2)
    if root not in _NOTES:
        return chord
    return f"{_NOTES[(_NOTES.index(root) + semitones) % 12]}{quality}"


def _normalize_chord_to_triad(chord: str):
    """Am7 → Am, Fmaj7 → F, G7 → G, Bm7b5 → Bm, C/G → C"""
    chord = chord.split('/')[0].strip()
    m = re.match(r'^([A-G][#b]?)(m(?!aj))?', chord)
    if not m:
        return None
    root = _normalize_note(m.group(1))
    quality = m.group(2) or ''
    return f"{root}{quality}" if root in _NOTES else None


def load_json(json_path: Path) -> dict:
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def load_audio(audio_path: Path):
    try:
        import librosa
    except ImportError:
        print("Erreur : librosa non installé. Lancer : pip install librosa soundfile")
        sys.exit(1)

    print(f"Chargement audio : {audio_path.name} …")
    y, sr = librosa.load(str(audio_path), sr=None, mono=True)
    duration = len(y) / sr
    print(f"  Durée     : {int(duration // 60)}:{int(duration % 60):02d}")
    print(f"  Fréquence : {sr} Hz")
    print(f"  Samples   : {len(y)}")
    return y, sr, duration


def format_duration(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


def fmt_time(seconds: float) -> str:
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


# ---------------------------------------------------------------------------
# A3 — Tempo + tonalité
# ---------------------------------------------------------------------------

def analyze_tempo_key(y, sr) -> dict:
    """A3 — Estimation tempo (beat_track) et tonalité (Krumhansl-Schmuckler)."""
    import librosa
    import numpy as np

    print("Analyse tempo et tonalité …")

    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])

    if len(beats) > 2:
        ibi = np.diff(beats).astype(float)
        tempo_conf = round(float(max(0.0, 1.0 - ibi.std() / (ibi.mean() + 1e-8))), 2)
    else:
        tempo_conf = 0.0

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)
    chroma_norm = chroma_mean / (chroma_mean.sum() + 1e-8)

    MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
    MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
    MAJOR = MAJOR / MAJOR.sum()
    MINOR = MINOR / MINOR.sum()

    scores = []
    for i, note in enumerate(_NOTES):
        rotated = np.roll(chroma_norm, -i)
        scores.append((float(np.corrcoef(rotated, MAJOR)[0, 1]), note, 'major'))
        scores.append((float(np.corrcoef(rotated, MINOR)[0, 1]), note, 'minor'))

    scores.sort(reverse=True)
    best_score, best_note, best_mode = scores[0]
    gap = scores[0][0] - scores[1][0]
    key_conf = round(min(1.0, max(0.0, gap / max(1.0 - scores[0][0], 0.05))), 2)
    display = _display_note(best_note, best_mode)

    return {
        "tempo_bpm": round(tempo, 1),
        "tempo_beats_count": int(len(beats)),
        "tempo_confidence": tempo_conf,
        "key_note": best_note,
        "key_note_display": display,
        "key_mode": best_mode,
        "key": f"{display} {best_mode}",
        "key_score_raw": round(best_score, 3),
        "key_confidence": key_conf,
        "confidence": {
            "tempo": tempo_conf,
            "key": key_conf,
            "structure": None,
            "chords": None,
            "chord_detail": None,
        },
    }


def compare_key_with_capo(audio: dict, song_meta: dict) -> dict:
    """Compare la tonalité audio avec la tonalité JSON en tenant compte du capo."""
    json_note_raw = song_meta.get("key") or ""
    json_mode = song_meta.get("key_mode") or "major"
    capo = int(song_meta.get("capo") or 0)

    json_note = _normalize_note(json_note_raw)
    if json_note not in _NOTES:
        return {"status": "inconnu", "sounding_key": None, "match": None}

    sounding_note = _NOTES[(_NOTES.index(json_note) + capo) % 12]
    sounding_display = _display_note(sounding_note, json_mode)

    audio_note = audio.get("key_note") or ""
    audio_mode = audio.get("key_mode") or ""

    key_match = (_normalize_note(audio_note) == sounding_note)
    mode_match = (audio_mode == json_mode)

    relative_match = False
    if not (key_match and mode_match):
        audio_idx = _NOTES.index(_normalize_note(audio_note)) if _normalize_note(audio_note) in _NOTES else -1
        sounding_idx = _NOTES.index(sounding_note)
        if json_mode == 'minor' and audio_mode == 'major':
            relative_match = (audio_idx == (sounding_idx + 3) % 12)
        elif json_mode == 'major' and audio_mode == 'minor':
            relative_match = (audio_idx == (sounding_idx - 3) % 12)

    if key_match and mode_match:
        status = "Conforme"
    elif relative_match:
        rel_display = _display_note(_NOTES[audio_idx], audio_mode)
        status = (f"Relatif conforme — {sounding_display} {json_mode} et "
                  f"{rel_display} {audio_mode} partagent la même gamme (ambiguïté KS normale)")
    elif key_match:
        status = f"Note conforme, mode diverge (JSON: {json_mode}, audio: {audio_mode})"
    elif mode_match:
        status = f"Mode conforme, note diverge (JSON+capo: {sounding_display}, audio: {audio.get('key_note_display')})"
    else:
        status = f"Divergence — JSON+capo: {sounding_display} {json_mode}, audio: {audio.get('key')}"

    return {
        "status": status,
        "json_key": f"{json_note_raw} {json_mode}",
        "capo": capo,
        "sounding_key": f"{sounding_display} {json_mode}",
        "audio_key": audio.get("key"),
        "match": key_match and mode_match,
        "relative_match": relative_match,
        "key_match": key_match,
        "mode_match": mode_match,
    }


# ---------------------------------------------------------------------------
# A4 — Structure
# ---------------------------------------------------------------------------

def analyze_structure(y, sr) -> dict:
    """A4 — Segmentation via novelty curve beat-synchrone + matrice de récurrence."""
    import librosa
    import numpy as np
    from scipy.ndimage import gaussian_filter1d

    print("Analyse de structure …")

    hop_length = 512
    _, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)

    if len(beats) < 4:
        return {"segments": None, "boundary_times": [], "repeat_count": None,
                "confidence_structure": None}

    # Chroma + MFCC beat-synchrones (chroma = harmonique, MFCC = timbral)
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=12, hop_length=hop_length)

    chroma_sync = librosa.util.sync(chroma, beats, aggregate=np.median)
    mfcc_sync = librosa.util.sync(mfcc, beats, aggregate=np.median)

    n = min(chroma_sync.shape[1], mfcc_sync.shape[1], len(beats))
    chroma_sync = chroma_sync[:, :n]
    mfcc_sync = mfcc_sync[:, :n]
    beats = beats[:n]

    if n < 6:
        return {"segments": None, "boundary_times": [], "repeat_count": None,
                "confidence_structure": None}

    # Novelty combinée : L2 norm des différences beat-à-beat chroma + MFCC normalisés
    chroma_n = chroma_sync / (np.linalg.norm(chroma_sync, axis=0, keepdims=True) + 1e-8)
    mfcc_n = mfcc_sync / (np.linalg.norm(mfcc_sync, axis=0, keepdims=True) + 1e-8)
    novelty = (np.linalg.norm(np.diff(chroma_n, axis=1), axis=0) +
               np.linalg.norm(np.diff(mfcc_n, axis=1), axis=0))

    sigma = max(1, n // 60)   # lissage léger (~2 secondes)
    novelty_smooth = gaussian_filter1d(novelty, sigma=sigma)

    nov_range = novelty_smooth.max() - novelty_smooth.min()
    novelty_norm = (novelty_smooth - novelty_smooth.min()) / nov_range if nov_range > 0 else novelty_smooth

    # min_dist : cible 10 secondes minimum entre deux frontières
    if len(beats) > 1:
        mean_ibi_secs = float(np.mean(np.diff(beats))) * hop_length / sr
        min_dist = max(3, int(10.0 / mean_ibi_secs))
    else:
        min_dist = 10

    peaks = librosa.util.peak_pick(
        novelty_norm,
        pre_max=min_dist, post_max=min_dist,
        pre_avg=min_dist, post_avg=min_dist,
        delta=0.03, wait=min_dist,
    )

    # Garder au plus ~15 frontières (cap de sécurité)
    if len(peaks) > 15:
        heights = novelty_norm[peaks]
        top_idx = np.argsort(heights)[::-1][:15]
        peaks = np.sort(peaks[top_idx])

    n_segments = len(peaks) + 1

    boundary_times = []
    if len(peaks) > 0:
        # peaks are indices into novelty (len n-1) → beats indices 0..n-2, safe
        boundary_frames = beats[peaks]
        times = librosa.frames_to_time(boundary_frames, sr=sr, hop_length=hop_length)
        boundary_times = [round(float(t), 1) for t in times]

    # Repeat detection via recurrence matrix
    norms = np.linalg.norm(chroma_sync, axis=0, keepdims=True) + 1e-8
    chroma_norm_cols = chroma_sync / norms
    R = librosa.segment.recurrence_matrix(chroma_norm_cols, mode='affinity', sym=True)
    np.fill_diagonal(R, 0)
    block = max(1, n // 10)
    repeat_count = min(8, int((R > 0.75).sum() / (2 * block)))

    conf = round(float(novelty_norm[peaks].mean()), 2) if len(peaks) > 0 else round(float(novelty_norm.max()), 2)

    return {
        "segments": n_segments,
        "boundary_times": boundary_times,
        "repeat_count": repeat_count,
        "confidence_structure": conf,
    }


# ---------------------------------------------------------------------------
# A5 — Accords (expérimental)
# ---------------------------------------------------------------------------

def analyze_chords(y, sr, json_chords_used: list, capo: int = 0) -> dict:
    """A5 — Estimation accords par templates triade sur chromagramme beat-synchrone."""
    import librosa
    import numpy as np

    print("Analyse des accords (expérimental) …")

    hop_length = 512
    _, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)

    chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
    chroma_sync = librosa.util.sync(chroma, beats, aggregate=np.median)

    # 24 templates : triades majeures et mineures
    def make_template(root_idx, intervals):
        t = np.zeros(12)
        for iv in intervals:
            t[(root_idx + iv) % 12] = 1.0
        norm = np.linalg.norm(t)
        return t / norm if norm > 0 else t

    templates = {}
    for i, note in enumerate(_NOTES):
        templates[note] = make_template(i, [0, 4, 7])
        templates[f"{note}m"] = make_template(i, [0, 3, 7])

    # Per-beat best chord
    labels = []
    for frame in range(chroma_sync.shape[1]):
        c = chroma_sync[:, frame]
        norm_c = np.linalg.norm(c)
        if norm_c < 1e-6:
            continue
        c_norm = c / norm_c
        best = max(templates, key=lambda k: float(np.dot(c_norm, templates[k])))
        labels.append(best)

    if not labels:
        return {
            "chord_progression": [], "chord_frequencies": [],
            "audio_chord_set": [], "json_chord_set_normalized": [],
            "missing_from_audio": [], "unexpected_in_audio": [],
            "suspicious_chords": [],
            "confidence": {"chords": 0.0, "chord_detail": 0.0},
        }

    total = len(labels)
    counter = Counter(labels)
    dominant = [(chord, round(count / total, 2)) for chord, count in counter.most_common(8)]
    dominant_names = [c for c, _ in dominant]

    # Normalise les accords JSON en triades, puis transpose du capo
    json_triads_raw = {t for c in json_chords_used if (t := _normalize_chord_to_triad(c))}
    json_triads = {_transpose_chord(t, capo) for t in json_triads_raw}
    audio_top = set(dominant_names)

    missing_from_audio = sorted(json_triads - audio_top)
    unexpected_in_audio = sorted(audio_top - json_triads)

    # Table de correspondance pour le rapport
    chord_match_table = []
    for chord in sorted(json_triads):
        freq = counter.get(chord, 0) / total
        chord_match_table.append({
            "chord": chord,
            "found": chord in audio_top,
            "freq": round(freq, 2),
        })

    suspicious = [
        {"chord": c, "signal": "Absent du top-8 audio", "note": "Non détecté — vérifier manuellement"}
        for c in missing_from_audio
    ]

    return {
        "chord_progression": dominant_names[:6],
        "chord_frequencies": dominant[:6],
        "chord_match_table": chord_match_table,
        "audio_chord_set": sorted(audio_top),
        "json_chord_set_normalized": sorted(json_triads),
        "missing_from_audio": missing_from_audio,
        "unexpected_in_audio": unexpected_in_audio,
        "suspicious_chords": suspicious,
        "confidence": {"chords": 0.45, "chord_detail": 0.30},
    }


# ---------------------------------------------------------------------------
# Recommandations
# ---------------------------------------------------------------------------

def build_recommendations(result: dict) -> list:
    recs = []
    audio = result["audio"]
    js = result["json"]
    kc = audio.get("key_comparison", {})

    # Tempo
    if js["tempo"] is None and audio.get("tempo_bpm"):
        recs.append(
            f"Tempo estimé {audio['tempo_bpm']} BPM — envisager "
            f"`\"tempo\": {int(round(audio['tempo_bpm']))}` dans le JSON "
            f"(confiance : {audio.get('tempo_confidence', '?')})"
        )
    elif js["tempo"] and audio.get("tempo_bpm"):
        diff = abs(float(audio["tempo_bpm"]) - float(js["tempo"]))
        if diff > 5:
            recs.append(
                f"Écart de tempo : JSON {js['tempo']} BPM vs audio {audio['tempo_bpm']} BPM "
                f"(écart {diff:.0f} BPM) — vérifier"
            )

    # Tonalité
    if kc.get("relative_match"):
        pass
    elif kc.get("match") is False:
        recs.append(f"Tonalité divergente : {kc.get('status')} — écouter avant toute correction")
    elif kc.get("key_match") and not kc.get("mode_match"):
        recs.append(f"Mode incertain : JSON {kc.get('json_key')}, audio suggère {kc.get('audio_key')}")

    # Structure
    seg = audio.get("segments")
    j_count = js.get("section_count", 0)
    if seg is not None and j_count > 0:
        diff = abs(seg - j_count)
        if diff >= 2:
            recs.append(
                f"Structure : audio détecte {seg} sections, JSON en annonce {j_count} "
                f"(écart {diff}) — vérifier les répétitions"
            )

    # Accords manquants
    for c in audio.get("missing_from_audio", []):
        recs.append(f"Accord `{c}` (JSON) absent du top-8 audio — vérifier manuellement")

    # Accords inattendus
    for c in audio.get("unexpected_in_audio", []):
        recs.append(f"Accord `{c}` détecté en audio mais absent du JSON — vérifier")

    return recs


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------

def analyze(json_path: Path, audio_path: Path):
    song = load_json(json_path)
    y, sr, duration = load_audio(audio_path)

    result = {
        "meta": {
            "title": song["meta"]["title"],
            "artist": song["meta"]["artist"],
            "slug": song["meta"]["slug"],
            "json_path": str(json_path),
            "audio_file": audio_path.name,
            "duration": duration,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
        },
        "json": {
            "key": song["meta"].get("key"),
            "key_mode": song["meta"].get("key_mode"),
            "capo": song["meta"].get("capo"),
            "tempo": song["meta"].get("tempo"),
            "section_count": len(song.get("structure_sequence", [])),
            "chords_used": song.get("chords_used", []),
        },
        "audio": {},
        "divergences": [],
        "recommendations": [],
    }

    # A3
    a3 = analyze_tempo_key(y, sr)
    result["audio"].update(a3)
    result["audio"]["key_comparison"] = compare_key_with_capo(a3, song["meta"])

    # A4
    a4 = analyze_structure(y, sr)
    result["audio"].update(a4)
    result["audio"]["confidence"].update({
        "structure": a4.get("confidence_structure"),
    })

    # A5
    capo = int(song["meta"].get("capo") or 0)
    a5 = analyze_chords(y, sr, result["json"]["chords_used"], capo=capo)
    result["audio"].update(a5)
    result["audio"]["confidence"].update(a5.get("confidence", {}))

    # Divergences
    result["divergences"] = [
        {"type": "accord_manquant", "detail": c,
         "note": "Présent dans JSON, absent du top-8 audio"}
        for c in a5.get("missing_from_audio", [])
    ] + [
        {"type": "accord_inattendu", "detail": c,
         "note": "Présent en audio, absent du JSON"}
        for c in a5.get("unexpected_in_audio", [])
    ]

    result["recommendations"] = build_recommendations(result)
    return result, y, sr, song


# ---------------------------------------------------------------------------
# Rapport Markdown
# ---------------------------------------------------------------------------

def write_report(result: dict, output_dir: Path) -> Path:
    slug = result["meta"]["slug"]
    report_path = output_dir / f"audio_report_{slug}.md"

    meta = result["meta"]
    js = result["json"]
    audio = result["audio"]
    divergences = result["divergences"]
    recommendations = result["recommendations"]
    kc = audio.get("key_comparison", {})

    def fmt(val, fallback="—"):
        return str(val) if val is not None else fallback

    lines = [
        f"# Rapport de comparaison audio — {meta['title']} ({meta['artist']})",
        f"Généré : {meta['generated_at']}  ",
        f"Fichier audio : `{meta['audio_file']}` ({format_duration(meta['duration'])})  ",
        f"JSON source : `{meta['json_path']}`",
        "",
        "---",
        "",
        "## Métadonnées",
        "",
        "| Dimension | Audio estimé | JSON actuel | Statut |",
        "|-----------|-------------|-------------|--------|",
    ]

    a_tempo = audio.get("tempo_bpm")
    j_tempo = js["tempo"]
    if j_tempo is None:
        tempo_status = "Info (JSON vide)"
    elif a_tempo and abs(float(a_tempo) - float(j_tempo)) < 5:
        tempo_status = "Conforme"
    else:
        tempo_status = "Écart"
    lines.append(f"| Tempo | {fmt(a_tempo, '—')} BPM | {fmt(j_tempo, 'null')} | {tempo_status} |")

    a_key_display = audio.get("key", "—")
    j_key_display = f"{js['key']} {js['key_mode']}" if js["key"] else "—"
    capo_note = f" (capo {js['capo']} → sonne {kc.get('sounding_key', '?')})" if js.get("capo") else ""
    lines.append(f"| Tonalité | {a_key_display} | {j_key_display}{capo_note} | {kc.get('status', '—')} |")
    lines.append(f"| Durée | {format_duration(meta['duration'])} | — | Info |")

    # --- Structure ---
    lines += ["", "---", "", "## Analyse de structure", ""]
    seg = audio.get("segments")
    j_count = js["section_count"]
    if seg is not None:
        diff = abs(seg - j_count)
        lines += [
            f"- Transitions détectées : **{seg}** sections",
            f"- Sections JSON (`structure_sequence`) : **{j_count}**",
            f"- Évaluation : {'Proche' if diff <= 1 else f'Écart de {diff} — vérifier les répétitions'}",
        ]
        repeat_count = audio.get("repeat_count")
        if repeat_count is not None:
            lines.append(f"- Zones répétées (matrice de récurrence) : {repeat_count}")
        boundary_times = audio.get("boundary_times", [])
        if boundary_times:
            strs = " | ".join(fmt_time(t) for t in boundary_times)
            lines.append(f"- Frontières estimées : {strs}")
        conf_struct = audio.get("confidence_structure")
        if conf_struct is not None:
            lines.append(f"\nConfiance structure : **{conf_struct}** (orientatif)")
    else:
        lines += [
            "_Analyse de structure non disponible._",
            f"- Sections JSON : **{j_count}**",
        ]

    # --- Harmonique ---
    lines += ["", "---", "", "## Analyse harmonique", "",
              "> Confiance faible — templates triades sur audio polyphonique.", ""]

    chord_prog = audio.get("chord_progression")
    if chord_prog:
        freq_list = audio.get("chord_frequencies", [])
        prog_str = "  ".join(
            f"{c} ({int(f*100)}%)" for c, f in freq_list
        )
        lines += [
            f"**Top 6 accords estimés :** {prog_str}",
            "",
            f"**Accords JSON (normalisés) :** `{' '.join(audio.get('json_chord_set_normalized', []))}`",
            "",
        ]

        # Correspondance JSON ↔ audio
        match_table = audio.get("chord_match_table", [])
        if match_table:
            lines += [
                "### Correspondance JSON ↔ audio",
                "",
                "| Accord JSON | Trouvé en audio | Fréquence estimée |",
                "|------------|----------------|-------------------|",
            ]
            for row in match_table:
                found_str = "Oui" if row["found"] else "**Non détecté**"
                freq_str = f"{int(row['freq']*100)}%" if row["freq"] > 0 else "< 1%"
                lines.append(f"| {row['chord']} | {found_str} | {freq_str} |")

        unexpected = audio.get("unexpected_in_audio", [])
        if unexpected:
            lines += [
                "",
                "### Accords audio non présents dans le JSON",
                "",
                "| Accord | Fréquence | Note |",
                "|--------|-----------|------|",
            ]
            freq_map = dict(audio.get("chord_frequencies", []))
            for c in unexpected:
                freq_str = f"{int(freq_map.get(c, 0)*100)}%" if c in freq_map else "—"
                lines.append(f"| {c} | {freq_str} | Absent du JSON — vérifier |")
    else:
        lines.append("_Analyse harmonique non disponible._")

    suspicious = audio.get("suspicious_chords", [])
    if suspicious:
        lines += ["", "### Accords suspects", "",
                  "| Accord JSON | Signal audio | Remarque |",
                  "|------------|-------------|----------|"]
        for s in suspicious:
            lines.append(f"| {s['chord']} | {s['signal']} | {s['note']} |")

    # --- Divergences ---
    lines += ["", "---", "", "## Divergences", ""]
    if divergences:
        lines += ["| Type | Accord | Note |",
                  "|------|--------|------|"]
        for d in divergences:
            lines.append(f"| {d['type']} | {d['detail']} | {d['note']} |")
    else:
        lines.append("Aucune divergence majeure détectée.")

    # --- Confiance ---
    lines += ["", "---", "", "## Scores de confiance", "",
              "| Dimension | Score | Fiabilité |",
              "|-----------|-------|-----------|"]
    conf = audio.get("confidence", {})
    lines += [
        f"| Tempo      | {fmt(conf.get('tempo'))}  | Élevée |",
        f"| Tonalité   | {fmt(conf.get('key'))}    | Élevée |",
        f"| Structure  | {fmt(conf.get('structure'), 'n/a')} | Orientatif |",
        f"| Progression| {fmt(conf.get('chords'), 'n/a')} | Faible (expérimental) |",
        f"| Accords    | {fmt(conf.get('chord_detail'), 'n/a')} | Faible (expérimental) |",
    ]

    # --- Recommandations ---
    lines += ["", "---", "", "## Recommandations", ""]
    if recommendations:
        for r in recommendations:
            lines.append(f"- [ ] {r}")
    else:
        lines.append("Aucune recommandation — tout semble conforme.")

    lines += [
        "", "---", "",
        "> Ce rapport est **orientatif**. Les estimations d'accords sont produites sur audio",
        "> polyphonique (guitare + voix + basse) avec des templates triades uniquement.",
        "> **La validation humaine reste obligatoire avant génération DOCX.**",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Compare un fichier JSON chords avec l'audio original (orientatif)."
    )
    parser.add_argument("json", type=Path, help="Chemin vers data/song_<slug>.json")
    parser.add_argument("audio", type=Path, help="Chemin vers le fichier audio (mp3/wav/ogg)")
    args = parser.parse_args()

    if not args.json.exists():
        print(f"Erreur : JSON introuvable : {args.json}")
        sys.exit(1)
    if not args.audio.exists():
        print(f"Erreur : fichier audio introuvable : {args.audio}")
        sys.exit(1)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    print(f"\n=== Comparaison audio — {args.json.stem} ===\n")

    result, y, sr, song = analyze(args.json, args.audio)
    audio = result["audio"]
    kc = audio.get("key_comparison", {})
    js = result["json"]

    print("\n--- A3 : Tempo + Tonalité ---")
    print(f"  Tempo     : {audio.get('tempo_bpm')} BPM  (conf. {audio.get('tempo_confidence')})")
    print(f"  Tonalité  : {audio.get('key')}  (KS score {audio.get('key_score_raw')}, conf. {audio.get('key_confidence')})")
    if js.get("capo"):
        print(f"  JSON+capo : {kc.get('sounding_key')}  (capo {js['capo']})")
    print(f"  Statut    : {kc.get('status', '—')}")

    seg = audio.get("segments")
    print(f"\n--- A4 : Structure ---")
    if seg is not None:
        print(f"  Sections  : {seg} (JSON : {js['section_count']})")
        print(f"  Répétitions détectées : {audio.get('repeat_count')}")
        bt = audio.get("boundary_times", [])
        if bt:
            print(f"  Frontières : {' | '.join(fmt_time(t) for t in bt)}")
        print(f"  Confiance : {audio.get('confidence_structure')}")

    print(f"\n--- A5 : Accords (expérimental) ---")
    prog = audio.get("chord_progression", [])
    if prog:
        print(f"  Top 6 : {' — '.join(prog)}")
        missing = audio.get("missing_from_audio", [])
        unexpected = audio.get("unexpected_in_audio", [])
        if missing:
            print(f"  Absents du top audio : {', '.join(missing)}")
        if unexpected:
            print(f"  Inattendus (audio only) : {', '.join(unexpected)}")

    if result["recommendations"]:
        print("\n--- Recommandations ---")
        for r in result["recommendations"]:
            print(f"  • {r}")

    report_path = write_report(result, output_dir)
    print(f"\nRapport : {report_path}")


if __name__ == "__main__":
    main()
