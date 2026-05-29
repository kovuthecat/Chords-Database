# CLAUDE.md

Instructions permanentes pour Claude Code dans ce projet.

## Rôle

Tu aides à maintenir et améliorer un **éditeur local de songbook guitare/chant**.

Le livrable final est un ensemble de fichiers `.pdf` clairs, imprimables et utilisables par :

- un guitariste ;
- un chanteur ;
- ou une personne qui chante en s'accompagnant à la guitare.

## Architecture du projet

Le projet ne crée **pas** les données chanson. Il **consomme** un JSON externe conforme au template.

```
JSON externe (fourni par l'utilisateur)
  → app.py (interface web locale, Flask)
    → scripts/validate_song_json.py   ← validation structure (slug, IDs, positions)
    → scripts/generate_docx.py        ← génération DOCX complet
    → scripts/backup.py               ← backup auto avant chaque sauvegarde
    → templates/_preview.html         ← aperçu HTML interactif (AJAX)
    → scripts/editor.py               ← édition inline (13 fonctions)
    → [validation utilisateur]
    → scripts/generate_docx.py        ← export 2 PDFs split
  → /library                          ← bibliothèque morceaux (recherche, export JSON)
  → data/backups/<slug>/              ← historique des sauvegardes
```

## Format d'entrée officiel

Le format d'entrée est défini par `examples/song_template.json` et documenté dans `schema/song_schema.json`.

Champs obligatoires :
- `meta.title`, `meta.artist`, `meta.slug`
- `sections` (liste non vide avec `id`, `type`)
- `structure_sequence` (liste non vide, tous les IDs doivent exister dans `sections`)

Champs fortement recommandés :
- `chords_used`
- `meta.key`, `meta.key_mode`, `meta.capo`
- `confidence.overall`
- `sections[*].lines` (pour les sections avec paroles)
- `sections[*].chord_grid` ou `summary_progression` (pour les sections instrumentales)
- `sections[*].performance_progression` (conducteur guitare précis)
- `sections[*].rhythm.pattern` et `rhythm.subdivision`

## Workflow obligatoire

1. Ouvrir `http://localhost:5000` (lancer avec `python app.py`).
2. Uploader un fichier JSON conforme au template.
3. L'application valide le JSON automatiquement.
4. Le DOCX et le PDF d'aperçu sont générés.
5. Vérifier l'aperçu dans le navigateur.
6. Cliquer "Valider et exporter 2 PDFs" pour exporter dans `PDF_EXPORT_DIR`.

**En ligne de commande :**
```bash
python main.py data/song_<slug>.json            # génère DOCX + PDF
python main.py data/song_<slug>.json --split-pdf # génère + exporte 3 PDFs
python main.py --validate data/song_<slug>.json  # valide seulement
python main.py --list                             # liste les chansons
```

## Hors périmètre absolu

- Génération ou extraction des données chanson (accords, paroles, structure).
- Recherche automatique de sources sur le web (Songsterr, Ultimate Guitar, etc.).
- Scraping de sites web.
- Web Fetch automatique.
- Analyse de fichiers audio (MP3, WAV, OGG).
- Transcription audio ou détection d'accords depuis l'audio.

## Contenu obligatoire du document final

### Fiche 1 — Paroles & Accords

- Titre, artiste, album (si présent), tonalité, capo, tempo si disponible
- Liste des accords utilisés
- Structure complète avec intro et parties instrumentales
- Paroles avec accords placés au-dessus des syllabes/mots concernés

### Fiche 2 — Mémo Guitare / Conducteur

- Une ou plusieurs lignes par section : label + progression + répétitions
- Depuis `performance_progression`, `summary_progression` ou `chord_grid`
- Champs optionnels : `rhythm_hint`, `mini_tab_hint`

La fiche "Comprendre le Morceau" (analyse harmonique) a été supprimée en v8.2 —
hors périmètre usage répétition/live. Script archivé dans `_archive/analysis.py`.

## Style du document

- Police Consolas (accords + paroles), Calibri (titres, méta).
- Accords : 13 pt, bold, bleu marine — paroles : 12 pt.
- Priorité à l'impression et à la lecture rapide.

## Export PDF split

Les 2 PDFs sont exportés dans `PDF_EXPORT_DIR` (défini dans `scripts/config.py`) :

```
Artiste - Titre - Paroles & Accords.pdf
Artiste - Titre - Mémo Guitare.pdf
```

## Règles de développement

- Toujours lire `PROJECT_BRIEF.md` / `DECISIONS.md` avant une modification.
- Utiliser `scripts/config.py` pour tous les chemins (ROOT_DIR, DATA_DIR, OUTPUT_DIR, PDF_EXPORT_DIR).
- Ne pas modifier la logique métier de `generate_docx.py`, `memo.py`, `analysis.py` sans nécessité.
- Ne pas ajouter de dépendances externes sans discussion.
- Ne jamais réintroduire de scraping web, web fetch automatique, ou analyse audio.
- Préserver la compatibilité des JSON existants dans `data/`.
- Le format JSON d'entrée est défini dans `examples/song_template.json` — ne pas le changer sans mettre à jour `schema/song_schema.json` et `validate_song_json.py`.

## Scripts conservés

| Fichier | Rôle |
|---|---|
| `app.py` | Interface web locale (Flask) |
| `main.py` | CLI simplifié |
| `scripts/validate_song_json.py` | Validation JSON (slug regex, IDs, positions) |
| `scripts/generate_docx.py` | Génération DOCX + PDF (2 fiches) |
| `scripts/memo.py` | Conducteur guitare (fiche mémo) |
| `scripts/editor.py` | Édition JSON ciblée (13 fonctions : paroles + instrumentaux + paroles inline) |
| `scripts/backup.py` | Backup/restauration automatique |
| `scripts/config.py` | Chemins centralisés (+ lecture `.env.local`) |
| `scripts/transpose.py` | Transposition automatique (tous accords × demi-tons) |
| `scripts/storage.py` | Couche de stockage abstraite (local par défaut, backend Supabase optionnel) |

## Scripts archivés

Les scripts suivants sont dans `_archive/` — non utilisés dans le workflow actuel :

- `collect.py` — parser texte brut (ancien workflow)
- `gemini_extract.py` — extraction PDF via Gemini API (abandonné)
- `gemini_client.py` — client Gemini API
- `reconstruct.py` — reconstruction multi-sources (non nécessaire avec JSON finalisé)
- `display_validation.py` — validation interactive en terminal (remplacée par l'interface web)
- `validate_harmony.py` — validation harmonique (non nécessaire avec JSON finalisé)
- `analysis.py` — fiche musicale / analyse harmonique (supprimée en v8.2, hors périmètre)
