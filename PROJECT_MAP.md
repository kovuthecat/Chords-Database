# PROJECT_MAP.md

Carte synthétique du projet (v10 — éditeur local de songbook guitare/chant).

## Vue d'ensemble

**Éditeur local de songbook guitare/chant** — génère 2 PDFs séparés à partir d'un JSON externe.
Interface web Flask locale. Édition interactive dans l'aperçu HTML.
Backup automatique à chaque sauvegarde. Mode répétition plein écran avec auto-scroll.
Transposition automatique. Bibliothèque avec recherche, filtres et statuts de révision.

Le projet **ne génère pas les données chanson**. Il consomme un JSON déjà finalisé.

## Flux principal

```
JSON externe (conforme à song_template_with_rhythm.json)
  → app.py (interface web, http://localhost:5000)
    → validate_song_json.py   ← validation structure JSON (slug, IDs, positions)
    → generate_docx.py        ← DOCX 2 pages + aperçu PDF
    → backup.py               ← backup timestampé avant chaque sauvegarde
    → [aperçu HTML interactif + édition inline]
      - accords (paroles + instrumental) : modifier / supprimer / insérer
      - paroles : édition texte inline
      - structure + rythme : éditeurs dédiés
    → generate_split_pdf()    ← export 2 PDFs dans PDF_EXPORT_DIR
  → /library                  ← bibliothèque morceaux (recherche, JSON, PDFs, suppression)
```

## Fichiers clés

| Fichier | Rôle |
|---|---|
| `song_template_with_rhythm.json` | Template de référence |
| `schema/song_schema.json` | Schéma JSON formel |
| `app.py` | Interface web Flask (port 5000) |
| `main.py` | CLI simplifié |
| `scripts/config.py` | Chemins centralisés (+ lecture `.env.local`) |
| `scripts/validate_song_json.py` | Validation JSON (slug regex, IDs, positions) |
| `scripts/generate_docx.py` | Génération DOCX + PDF split |
| `scripts/memo.py` | Logique fiche mémo structure guitare |
| `scripts/editor.py` | 13 fonctions d'édition JSON ciblée |
| `scripts/backup.py` | Backup / restauration automatique |
| `scripts/transpose.py` | Transposition automatique (tous accords × demi-tons) |
| `scripts/storage.py` | Couche de stockage abstraite (local / supabase) |

## Templates HTML

| Template | Rôle |
|---|---|
| `templates/index.html` | Accueil — upload JSON |
| `templates/library.html` | Bibliothèque — liste, recherche, actions |
| `templates/song.html` | Fiche chanson — aperçu + éditeurs + backups |
| `templates/_preview.html` | Fragment aperçu interactif (inclus + AJAX) |

## Routes principales (app.py)

| Route | Méthode | Rôle |
|---|---|---|
| `/` | GET | Accueil + upload |
| `/upload` | POST | Traitement upload JSON |
| `/library` | GET | Bibliothèque des morceaux |
| `/song/<slug>` | GET | Fiche chanson + éditeurs + backup |
| `/song/<slug>/export-split` | POST | Valider + exporter 2 PDFs |
| `/song/<slug>/regenerate` | POST | Régénérer depuis JSON |
| `/song/<slug>/save-all` | POST | Sauvegarder structure + rythme (AJAX) |
| `/song/<slug>/delete` | POST | Supprimer une chanson |
| `/song/<slug>/download-json` | GET | Télécharger le JSON |
| `/song/<slug>/restore/<filename>` | POST | Restaurer un backup |
| `/song/<slug>/preview-html` | GET | Fragment preview AJAX |
| `/song/<slug>/chord-at/update` | POST | Modifier un accord (paroles) |
| `/song/<slug>/chord-at/delete` | POST | Supprimer un accord (paroles) |
| `/song/<slug>/chord-at/insert` | POST | Insérer un accord (paroles) |
| `/song/<slug>/instr-chord/update` | POST | Modifier un accord instrumental |
| `/song/<slug>/instr-chord/delete` | POST | Supprimer un accord instrumental |
| `/song/<slug>/instr-chord/insert` | POST | Insérer un accord instrumental |
| `/song/<slug>/lyrics-at/update` | POST | Modifier le texte de paroles |
| `/export/<filename>` | GET | Servir un PDF exporté |
| `/output/<filename>` | GET | Servir un fichier output/ |

## Dossiers

| Dossier | Contenu |
|---|---|
| `data/` | JSON chansons (`song_<slug>.json`) |
| `data/backups/<slug>/` | Backups timestampés (20 max par chanson) |
| `output/` | DOCX + PDF générés (non versionnés) |
| `templates/` | Templates HTML Flask |
| `tests/` | 129 tests unitaires + Flask |
| `_archive/` | Anciens scripts (workflow Gemini/collect, analysis.py) |

## Tests

| Fichier | Tests | Portée |
|---|---|---|
| `tests/test_app.py` | 15 | Routes Flask, upload, backup, restauration |
| `tests/test_editor.py` | 47 | Fonctions editor.py |
| `tests/test_memo.py` | 53 | Logique mémo |
| `tests/test_validate_json.py` | 14 | Validation JSON |

**Total : 129 tests — 0 échec.**

## Chansons produites

Voir `data/song_*.json` et `output/song_*.docx`.
Les PDFs exportés sont dans `PDF_EXPORT_DIR` (configurable via `.env.local`).
