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
import sys
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


def analyze_tempo_key(y, sr) -> dict:
    """A3 — Estimation tempo (beat_track) et tonalité (Krumhansl-Schmuckler)."""
    import librosa
    import numpy as np

    print("Analyse tempo et tonalité …")

    # Tempo
    tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo)[0])

    if len(beats) > 2:
        ibi = np.diff(beats).astype(float)
        tempo_conf = round(float(max(0.0, 1.0 - ibi.std() / (ibi.mean() + 1e-8))), 2)
    else:
        tempo_conf = 0.0

    # Tonalité — profils Krumhansl-Schmuckler
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

    # Relatif major/mineur : même gamme, tonal center perçu différemment par KS
    relative_match = False
    if not (key_match and mode_match):
        audio_idx = _NOTES.index(_normalize_note(audio_note)) if _normalize_note(audio_note) in _NOTES else -1
        sounding_idx = _NOTES.index(sounding_note)
        if json_mode == 'minor' and audio_mode == 'major':
            # relatif majeur = tonique mineure + 3 demi-tons
            relative_match = (audio_idx == (sounding_idx + 3) % 12)
        elif json_mode == 'major' and audio_mode == 'minor':
            # relatif mineur = tonique majeure - 3 demi-tons
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


def build_recommendations(result: dict) -> list:
    recs = []
    audio = result["audio"]
    js = result["json"]
    kc = audio.get("key_comparison", {})

    if js["tempo"] is None and audio.get("tempo_bpm"):
        recs.append(
            f"Tempo estimé {audio['tempo_bpm']} BPM — envisager `\"tempo\": {int(round(audio['tempo_bpm']))}` "
            f"dans le JSON (confiance : {audio.get('tempo_confidence', '?')})"
        )
    elif js["tempo"] and audio.get("tempo_bpm"):
        diff = abs(float(audio["tempo_bpm"]) - float(js["tempo"]))
        if diff > 5:
            recs.append(
                f"Écart de tempo : JSON {js['tempo']} BPM vs audio {audio['tempo_bpm']} BPM "
                f"(écart {diff:.0f} BPM) — vérifier"
            )

    if kc.get("relative_match"):
        pass  # relatif conforme — pas de recommandation
    elif kc.get("match") is False:
        recs.append(f"Tonalité divergente : {kc.get('status')} — écouter avant toute correction")
    elif kc.get("key_match") and not kc.get("mode_match"):
        recs.append(
            f"Mode incertain : JSON indique {kc.get('json_key')}, audio suggère {kc.get('audio_key')}"
        )

    return recs


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
    result["recommendations"] = build_recommendations(result)

    # A4–A6 : à venir
    return result, y, sr, song


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

    # Tempo
    a_tempo = audio.get("tempo_bpm")
    j_tempo = js["tempo"]
    if j_tempo is None:
        tempo_status = "Info (JSON vide)"
    elif a_tempo and abs(float(a_tempo) - float(j_tempo)) < 5:
        tempo_status = "Conforme"
    else:
        tempo_status = "Écart"
    lines.append(f"| Tempo | {fmt(a_tempo, '—')} BPM | {fmt(j_tempo, 'null')} | {tempo_status} |")

    # Tonalité — capo-aware
    a_key_display = audio.get("key", "—")
    j_key_display = f"{js['key']} {js['key_mode']}" if js["key"] else "—"
    capo_note = f" (capo {js['capo']} → sonne {kc.get('sounding_key', '?')})" if js.get("capo") else ""
    lines.append(f"| Tonalité | {a_key_display} | {j_key_display}{capo_note} | {kc.get('status', '—')} |")

    # Durée
    lines.append(f"| Durée | {format_duration(meta['duration'])} | — | Info |")

    lines += ["", "---", "", "## Analyse de structure", ""]
    seg = audio.get("segments")
    j_count = js["section_count"]
    if seg is not None:
        diff = abs(seg - j_count)
        lines += [
            f"- Transitions majeures détectées : **{seg}**",
            f"- Sections dans `structure_sequence` JSON : **{j_count}**",
            f"- Évaluation : {'Proche' if diff <= 1 else f'Écart de {diff}'}",
        ]
        if audio.get("repeat_count") is not None:
            lines.append(f"- Zones répétées détectées : {audio['repeat_count']}")
    else:
        lines += [
            "_Analyse de structure non disponible (étape A4 non encore implémentée)._",
            f"- Sections JSON : **{j_count}**",
        ]

    lines += ["", "---", "", "## Analyse harmonique", ""]
    chord_prog = audio.get("chord_progression")
    if chord_prog:
        lines += [
            f"- Progression dominante estimée : `{' — '.join(chord_prog[:8])}`",
            f"- Accords JSON : `{' '.join(js['chords_used'])}`",
        ]
    else:
        lines.append("_Analyse harmonique non disponible (étape A5 non encore implémentée)._")

    suspicious = audio.get("suspicious_chords", [])
    if suspicious:
        lines += ["", "### Accords suspects", "",
                  "| Accord JSON | Signal audio | Remarque |",
                  "|------------|-------------|----------|"]
        for s in suspicious:
            lines.append(f"| {s['chord']} | {s['signal']} | {s['note']} |")

    lines += ["", "### Divergences", ""]
    if divergences:
        lines += ["| Section | JSON | Audio estimé | Confiance |",
                  "|---------|------|-------------|-----------|"]
        for d in divergences:
            lines.append(f"| {d['section']} | {d['json']} | {d['audio']} | {d['confidence']} |")
    else:
        lines.append("Aucune divergence harmonique détectée (A5 non encore disponible).")

    lines += ["", "---", "", "## Scores de confiance", "",
              "| Dimension | Score | Note |",
              "|-----------|-------|------|"]
    conf = audio.get("confidence", {})
    lines += [
        f"| Tempo           | {fmt(conf.get('tempo'))}  | Fiable |",
        f"| Tonalité        | {fmt(conf.get('key'))}    | Fiable |",
        f"| Structure       | {fmt(conf.get('structure'), 'n/a')} | Orientatif (A4) |",
        f"| Progression     | {fmt(conf.get('chords'), 'n/a')} | Orientatif (A5) |",
        f"| Accords détail  | {fmt(conf.get('chord_detail'), 'n/a')} | Expérimental (A5) |",
    ]

    lines += ["", "---", "", "## Recommandations", ""]
    if recommendations:
        for r in recommendations:
            lines.append(f"- [ ] {r}")
    else:
        lines.append("Aucune recommandation — tonalité et tempo conformes.")

    lines += [
        "", "---", "",
        "> Ce rapport est **orientatif**. Les estimations sont produites sur audio polyphonique",
        "> (guitare + voix + basse). **La validation humaine reste obligatoire avant génération DOCX.**",
    ]

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


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

    print("\n--- Résultats A3 ---")
    print(f"  Tempo estimé  : {audio.get('tempo_bpm')} BPM  "
          f"(confiance : {audio.get('tempo_confidence')})")
    print(f"  Tonalité audio: {audio.get('key')}  "
          f"(score KS : {audio.get('key_score_raw')}, confiance : {audio.get('key_confidence')})")
    if js.get("capo"):
        print(f"  JSON key+capo : {kc.get('sounding_key')}  (capo {js['capo']})")
    print(f"  Statut        : {kc.get('status', '—')}")

    if result["recommendations"]:
        print("\n  Recommandations :")
        for r in result["recommendations"]:
            print(f"    • {r}")

    report_path = write_report(result, output_dir)
    print(f"\nRapport généré : {report_path}")


if __name__ == "__main__":
    main()
