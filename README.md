# Chords — éditeur local de songbook guitare/chant

Éditeur local qui génère des **fiches PDF** (accords + paroles) pour guitariste et chanteur,
à partir d'un **fichier JSON fourni en entrée**.

Chaque document contient deux fiches :
1. **Paroles & Accords** — paroles avec accords positionnés, intro, sections instrumentales
2. **Mémo Guitare** — conducteur guitare multi-lignes, rythmes section par section

> **Principe** : le projet ne crée pas les données chanson.
> Il consomme un JSON externe conforme au template, permet l'édition interactive, et génère les documents.

## Installation

```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # Linux / macOS
pip install -r requirements.txt
```

## Lancer l'interface web

```bash
python app.py
```

Ouvrir **http://localhost:5000** dans le navigateur.

## Workflow

1. Créer un JSON conforme à `song_template_with_rhythm.json` (via Claude AI ou manuellement).
2. Ouvrir l'interface web : `python app.py`.
3. Uploader le JSON.
4. L'application valide le JSON, génère le DOCX et un aperçu HTML interactif.
5. Éditer directement dans l'aperçu :
   - **Accords** : clic = modifier/supprimer, survol ligne = ajouter
   - **Sections instrumentales** : insertion entre les accords
   - **Paroles** : clic sur une ligne = éditer le texte inline
6. Cliquer **"Valider et exporter 2 PDFs"** pour exporter les fiches dans `PDF_EXPORT_DIR`.
7. Consulter la **Bibliothèque** (`/library`) pour gérer, rechercher, télécharger et restaurer les morceaux.

## Backup automatique

Chaque sauvegarde crée automatiquement un backup dans `data/backups/<slug>/`.
Restauration en un clic depuis la section "Historique / Backups" de la fiche chanson.

## Configuration

Créer `.env.local` à la racine pour personnaliser le dossier d'export PDF :

```
PDF_EXPORT_DIR=C:\Users\kovu\SynologyDrive\Thibault\Guitartabs\Chords
```

## Ligne de commande

```bash
python main.py data/song_<slug>.json            # génère DOCX + PDF
python main.py data/song_<slug>.json --split-pdf # génère + exporte 2 PDFs
python main.py --validate data/song_<slug>.json  # valide seulement
python main.py --list                             # liste les chansons
```

## Format d'entrée

Le fichier JSON doit être conforme au template `song_template_with_rhythm.json`.
Le schéma est documenté dans `schema/song_schema.json`.

Champs obligatoires : `meta.title`, `meta.artist`, `meta.slug` (regex `^[a-z0-9_-]+$`),
`sections`, `structure_sequence`.

## Structure du projet

```
Chords/
├── app.py                          ← interface web locale (Flask)
├── main.py                         ← CLI simplifié
├── requirements.txt
├── song_template_with_rhythm.json  ← template de référence
├── schema/song_schema.json         ← schéma JSON officiel
├── data/
│   ├── song_*.json                 ← chansons importées
│   └── backups/<slug>/             ← backups timestampés
├── output/                         ← DOCX + PDF générés
├── templates/
│   ├── index.html                  ← accueil + upload
│   ├── song.html                   ← fiche chanson + éditeurs + aperçu
│   ├── _preview.html               ← fragment aperçu interactif (AJAX)
│   └── library.html                ← bibliothèque des morceaux
├── scripts/
│   ├── config.py                   ← chemins centralisés (+ .env.local)
│   ├── validate_song_json.py       ← validation JSON entrant (renforcée)
│   ├── generate_docx.py            ← génération DOCX + PDF (2 fiches)
│   ├── editor.py                   ← édition JSON ciblée (13 fonctions)
│   ├── backup.py                   ← backup/restauration automatique
│   └── memo.py                     ← conducteur guitare
├── tests/
│   ├── test_app.py                 ← 15 tests Flask
│   ├── test_validate_json.py
│   ├── test_memo.py
│   └── test_editor.py
└── _archive/                       ← anciens scripts (workflow précédent)
```

## Tests

```bash
python -m pytest tests/ -v
```

**129 tests — 0 échec.**

## Export PDF split

Les 2 PDFs sont exportés dans le dossier configuré (`.env.local` ou `scripts/config.py`) :

- `Artiste - Titre - Paroles & Accords.pdf`
- `Artiste - Titre - Mémo Guitare.pdf`

## Ce qui est hors périmètre

- Génération ou extraction des données chanson depuis le web.
- Scraping, Web Fetch automatique.
- Analyse audio (MP3, WAV, OGG).
- Base de données, authentification, déploiement web.
- Framework frontend moderne (React, Vue, Svelte).
