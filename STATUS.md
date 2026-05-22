# STATUS.md

> Dernière mise à jour : 2026-05-22 (module audio A1+A2)

## Phase actuelle

Phase 2 — pipeline complet opérationnel, 6 chansons générées, format DOCX affiné.

## Ce qui fonctionne

### Pipeline complet (T1→T7)

- `schema/song_schema.json` : schéma JSON de référence annoté.
- `scripts/collect.py` : init JSON, parser texte chord multi-lignes, ingestion sources, statut.
- `scripts/reconstruct.py` : unification multi-sources, source_agreement, divergences.
- `scripts/validate_harmony.py` : détection tonalité, check diatonique, scoring, capo.
- `scripts/display_validation.py` : brouillon terminal formaté + boucle OK/corrections.
- `scripts/generate_docx.py` : génération DOCX depuis JSON validé (Consolas, Calibri, keep_with_next).

### Fonctionnalités parser

- Grilles d'accords multi-lignes (concaténation `\n`).
- Accords slash numériques : `Am7/4`, `C/G`, `F/A`.
- Accords altérés : `Bm7b5`, `Asus4`, `b5`, `#11`, etc.
- Sections françaises et anglaises reconnues.
- Reprises détectées (`x2`, `×3`).
- Métadonnées capo/key/tonalité filtrées (pas créées comme section).
- Outro non-instrumental par défaut.

### Fonctionnalités DOCX

- Police Consolas (accords + paroles) / Calibri (titres, méta).
- Accords : 13 pt, bold, bleu marine — paroles : 12 pt.
- `keep_with_next` : accords jamais séparés des paroles par saut de page.
- Grilles multi-lignes rendues sur plusieurs paragraphes.
- Sections toujours rendues complètes (pas de "→ reprise").
- Marges 2.5 cm gauche / 2 cm autres.

### Chansons produites

| Fichier | Statut |
|---|---|
| `output/song_moriarty-jimmy.docx` | Généré et relu — v2 avec corrections utilisateur |
| `output/song_moriarty-jimmy-v2.docx` | Version reformatée (Consolas) |
| `output/song_pink-floyd-wish-you-were-here.docx` | Généré — 3 sources croisées |
| `output/song_neil-young-heart-of-gold.docx` | Généré — 2 sources, refrain extrait |
| `output/song_zaho-de-sagazan-la-symphonie-des-eclairs.docx` | Généré — source PDF unique |
| `output/song_muse-endlessly.docx` | Généré — source PDF unique |

## Bugs corrigés

- Regex `tonali...` ne capturait pas le `m` de "Am" → corrigé.
- `key_mode` non déduit depuis la clé brute "Am" → normalisé.
- Grilles multi-lignes écrasées (overwrite) → concaténation `\n`.
- Outro auto-marqué instrumental → corrigé (type-driven uniquement pour intro/interlude/solo).
- Faux positif capo pour tonalités relatives maj/min → tolérance ±3 demi-tons.
- Regex chord étendu : `Am7/4`, `Bm7b5`, `Asus4`, `F/A` maintenant reconnus.

## Conventions retenues (issues des corrections utilisateur)

- **Source de référence** : La Boîte à Chansons > Ultimate Guitar > Songsterr.
- **Accords simplifiés** : préférer G à G7, A à Am7/4 si l'utilisateur le demande.
- **Reprises** : toujours réécrire complètement les paroles + accords (pas de shorthand).
- **Accords empruntés** (Cm, Fm, Bb) : avertissement low uniquement, pas bloquant.

## Module audio (en cours — Phase A)

Étude de faisabilité réalisée le 2026-05-22. Architecture MVP définie :
- `audio/` ignoré par Git (fichiers locaux uniquement)
- `scripts/audio_compare.py` → rapport orientatif dans `output/audio_report_<slug>.md`
- Dépendance unique : `librosa` + `soundfile`

| Tâche | Statut |
|-------|--------|
| A1 — `audio/` + `.gitkeep` + `.gitignore` | Fait |
| A2 — squelette `audio_compare.py` (argparse, chargement, rapport vide) | Fait |
| A3 — tempo + tonalité (librosa) | Fait — testé sur Jimmy (127.8 BPM, relatif conforme) |
| A4 — structure (matrice de récurrence) | À faire |
| A5 — chromagramme + templates accords | À faire (expérimental) |
| A6 — divergences JSON/audio | À faire |
| A7 — génération rapport Markdown | Squelette présent, enrichissement A3–A6 |
| A8 — tests sur 5 chansons + calibrage | À faire |

## Prochaines étapes suggérées

1. A3 — Tempo + tonalité dans `audio_compare.py` (1h).
2. `main.py` — orchestration complète en une commande (`titre + artiste → DOCX`).
3. Affiner le placement accords/paroles sur les syllabes exactes (review manuelle).
4. Ajouter un champ `album` visible dans le DOCX (actuellement en meta JSON uniquement).

## Architecture actuelle

```
Chords/
├── schema/
│   └── song_schema.json         ← schéma de référence annoté
├── data/
│   ├── song_moriarty-jimmy.json
│   ├── song_pink-floyd-wish-you-were-here.json
│   ├── song_neil-young-heart-of-gold.json
│   ├── song_zaho-de-sagazan-la-symphonie-des-eclairs.json
│   └── song_muse-endlessly.json
├── audio/                       ← ignoré Git — y placer mp3/wav/ogg
├── output/
│   ├── *.docx                   ← documents générés
│   └── audio_report_*.md        ← rapports comparaison audio (à venir)
├── scripts/
│   ├── collect.py               ← T2 — init + parser + ingestion
│   ├── reconstruct.py           ← T3 — unification multi-sources
│   ├── validate_harmony.py      ← T4 — scoring harmonique
│   ├── display_validation.py    ← T5 — validation utilisateur terminal
│   ├── generate_docx.py         ← T7 — génération DOCX finale
│   └── audio_compare.py         ← A2 — comparaison audio (squelette)
└── [fichiers contexte projet]
```
