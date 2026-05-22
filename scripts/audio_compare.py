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


def analyze(json_path: Path, audio_path: Path) -> dict:
    """Collecte toutes les métriques audio et construit le dict résultat."""
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
        # Remplis par les étapes A3–A6
        "audio": {},
        "divergences": [],
        "recommendations": [],
    }
    return result, y, sr, song


def write_report(result: dict, output_dir: Path) -> Path:
    slug = result["meta"]["slug"]
    report_path = output_dir / f"audio_report_{slug}.md"

    meta = result["meta"]
    js = result["json"]
    audio = result["audio"]
    divergences = result["divergences"]
    recommendations = result["recommendations"]

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
    tempo_status = "Info (JSON vide)" if j_tempo is None else (
        "Conforme" if a_tempo and abs(float(a_tempo) - float(j_tempo)) < 5 else "Écart"
    )
    lines.append(f"| Tempo | {fmt(a_tempo, '—')} BPM | {fmt(j_tempo, 'null')} | {tempo_status} |")

    # Tonalité
    a_key = audio.get("key")
    j_key = f"{js['key']} {js['key_mode']}" if js["key"] else "—"
    key_status = "—"
    if a_key and js["key"]:
        key_status = "Conforme" if a_key.lower().replace(" ", "") in j_key.lower().replace(" ", "") else "Écart — vérifier"
    lines.append(f"| Tonalité | {fmt(a_key)} | {j_key} | {key_status} |")

    # Durée
    lines.append(f"| Durée | {format_duration(meta['duration'])} | — | Info |")

    lines += [
        "",
        "---",
        "",
        "## Analyse de structure",
        "",
    ]

    seg = audio.get("segments")
    j_count = js["section_count"]
    if seg is not None:
        diff = abs(seg - j_count)
        status = "Proche" if diff <= 1 else f"Écart de {diff}"
        lines += [
            f"- Transitions majeures détectées : **{seg}**",
            f"- Sections dans `structure_sequence` JSON : **{j_count}**",
            f"- Évaluation : {status}",
        ]
        reps_audio = audio.get("repeat_count")
        if reps_audio is not None:
            lines.append(f"- Zones répétées détectées : {reps_audio}")
    else:
        lines += [
            "_Analyse de structure non disponible (étape A4 non implémentée)._",
            f"- Sections JSON : **{j_count}**",
        ]

    conf_struct = audio.get("confidence_structure")
    if conf_struct is not None:
        lines.append(f"\nConfiance structure : **{conf_struct}**")

    lines += [
        "",
        "---",
        "",
        "## Analyse harmonique",
        "",
    ]

    chord_prog = audio.get("chord_progression")
    if chord_prog:
        lines += [
            f"- Tonalité audio confirmée : {fmt(a_key)} (score {audio.get('key_confidence', '—')})",
            f"- Progression dominante estimée : `{' — '.join(chord_prog[:8])}`",
            f"- Accords JSON : `{' '.join(js['chords_used'])}`",
        ]
    else:
        lines.append("_Analyse harmonique non disponible (étape A5 non implémentée)._")

    suspicious = audio.get("suspicious_chords", [])
    if suspicious:
        lines += ["", "### Accords suspects", ""]
        lines += ["| Accord JSON | Signal audio | Remarque |", "|------------|-------------|----------|"]
        for s in suspicious:
            lines.append(f"| {s['chord']} | {s['signal']} | {s['note']} |")

    lines += ["", "### Divergences", ""]
    if divergences:
        lines += ["| Section | JSON | Audio estimé | Confiance |", "|---------|------|-------------|-----------|"]
        for d in divergences:
            lines.append(f"| {d['section']} | {d['json']} | {d['audio']} | {d['confidence']} |")
    else:
        lines.append("Aucune divergence majeure détectée.")

    lines += [
        "",
        "---",
        "",
        "## Scores de confiance",
        "",
        "| Dimension | Score | Note |",
        "|-----------|-------|------|",
    ]

    conf = audio.get("confidence", {})
    lines += [
        f"| Tempo           | {fmt(conf.get('tempo'), '—')}  | Fiable |",
        f"| Tonalité        | {fmt(conf.get('key'), '—')}    | Fiable |",
        f"| Structure       | {fmt(conf.get('structure'), '—')} | Orientatif |",
        f"| Progression     | {fmt(conf.get('chords'), '—')} | Orientatif |",
        f"| Accords détail  | {fmt(conf.get('chord_detail'), '—')} | Expérimental |",
    ]

    lines += [
        "",
        "---",
        "",
        "## Recommandations",
        "",
    ]
    if recommendations:
        for r in recommendations:
            lines.append(f"- [ ] {r}")
    else:
        lines.append("_Aucune recommandation générée._")

    lines += [
        "",
        "---",
        "",
        "> Ce rapport est **orientatif**. Les scores d'accord sont issus d'une estimation",
        "> chromagramme sur audio polyphonique (guitare + voix + basse).",
        "> **La validation humaine reste obligatoire avant génération DOCX.**",
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

    # Étapes A3–A6 : non encore implémentées
    # result["audio"] sera enrichi par : analyze_tempo_key(), analyze_structure(), analyze_chords()

    report_path = write_report(result, output_dir)
    print(f"\nRapport généré : {report_path}")
    print("(Analyse audio non encore disponible — squelette A2 uniquement)")


if __name__ == "__main__":
    main()
