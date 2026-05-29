# ROADMAP.md

## MVP — Terminé ✓

- [x] Pipeline complet : titre → collecte → reconstruction → validation → DOCX.
- [x] Parser texte chord : sections FR/EN, grilles multi-lignes, accords altérés.
- [x] Reconstruction multi-sources avec scoring de confiance et détection de divergences.
- [x] Validation harmonique : tonalité, accords hors gamme, cohérence capo.
- [x] DOCX lisible : Consolas, accords visibles, keep_with_next, reprises complètes.
- [x] Fiche mémo structure guitare (2e page obligatoire).
- [x] 6 chansons traitées.

## Version 1 — Stabilisation P1–P5 (terminé) ✓

- [x] Orchestrateur `main.py` + chemins centralisés `config.py`.
- [x] Tests unitaires (pytest).
- [x] Export PDF split 2 fiches : Paroles & Accords + Mémo Guitare.
- [x] Conducteur guitare multi-lignes (fiche mémo).

## Version 2 — P8 : Interface web locale (terminé) ✓

- [x] Interface Flask locale : upload JSON → validation → génération DOCX + aperçu.
- [x] Aperçu HTML interactif : clic = modifier/supprimer accord, survol = insérer.
- [x] AJAX : sauvegarde sans rechargement, rafraîchissement partiel du preview.
- [x] `scripts/editor.py` : fonctions d'édition JSON (replace, structure, rhythm, delete/update/insert).
- [x] 3 éditeurs dans la fiche chanson : structure, remplacement accords, rythme.
- [x] Export split : 2 PDFs (Paroles & Accords + Mémo Guitare).
- [x] Bibliothèque `/library` : tous les morceaux, fiches PDF directement accessibles.
- [x] Accords instrumentaux cliquables (pp, chord_grid, summary_progression).
- [x] Bouton global "Sauvegarder et rafraîchir" (structure + rythme en un clic AJAX).
- [x] Suppression d'une chanson depuis la bibliothèque.

## Version 3 — P9 : Sécurité + confort d'édition + robustesse (terminé) ✓

- [x] **Backup automatique** : chaque sauvegarde crée un backup timestampé dans `data/backups/<slug>/`.
- [x] **Restauration** : section "Historique / Backups" dans la fiche chanson, bouton Restaurer.
- [x] **Confirmations** : `confirm()` avant suppression d'accord, section, ou restauration.
- [x] **Insertion instrumentale** : points `+` entre les accords des sections pp/cg/sp.
- [x] **Édition paroles inline** : clic sur ligne de paroles → input in-place → sauvegarde AJAX.
- [x] **Recherche bibliothèque** : filtrage live (titre, artiste, album) sans backend.
- [x] **Export JSON** : bouton "JSON" sur chaque card de la bibliothèque.
- [x] **PDF_EXPORT_DIR configurable** : lecture depuis `.env.local` (pas de python-dotenv requis).
- [x] **Validation renforcée** : slug regex, IDs sections, ordre/collision positions.
- [x] **Tests Flask** : 15 tests `app.test_client()` — 129 tests au total, 0 échec.

## Version 4 — P10 : Mode répétition + ergonomie + bibliothèque (terminé) ✓

- [x] **Mode répétition** : 2 vues plein écran sans éléments d'édition (`rehearsal_chords.html`, `rehearsal_memo.html`).
- [x] **Auto-scroll** : vitesse réglable, start/stop Espace, persistance localStorage.
- [x] **Transposition automatique** : tous les accords × demi-tons, UI ±1/±2 + custom, `scripts/transpose.py`.
- [x] **Statut de révision** (`review_status`) : ok / to_review / draft, badges bibliothèque, select AJAX inline.
- [x] **Filtres bibliothèque** : tonalité, capo, statut révision — filtrage JS local.
- [x] **Raccourcis clavier** song.html : S/E/L/F (non déclenchés depuis inputs).
- [x] **Export JSON depuis la fiche chanson** : bouton "Télécharger JSON" dans la section Actions.
- [x] **178 tests au total — 0 régression.**

## Version 5 — P11 : Simplification interface (terminé) ✓

- [x] **Page d'accueil** : `/` redirige vers `/library` — `/add` pour l'ajout.
- [x] **Navigation icônes** : headers avec emojis (📚 Biblio · ➕ Ajouter · 🎵 · 🎸 · 📄).
- [x] **Cards bibliothèque simplifiées** : actions primaires + bloc "Options avancées" (`<details>`).
- [x] **Labels nettoyés** : "Exporter les fiches", "Mettre à jour les fiches".
- [x] **Transposition améliorée** : tonalité actuelle + capo + estimation temps réel + confirmation enrichie.
- [x] **Remplacement d'accord** déplacé dans "Options avancées" de song.html.

## Version 6 — P12 : Édition accords + rythme (terminé) ✓

- [x] **Déplacement d'accord** : boutons ← / → dans le popup + champ position exacte (Définir).
- [x] **Routes move/set-position** : `POST /chord-at/move` et `POST /chord-at/set-position`.
- [x] **Raccourcis rythme** : `d`→↓ · `u`→↑ dans les inputs de pattern (keydown intercepté).
- [x] **Bibliothèque de présets** : `static/rhythm_patterns.json` (8 présets : DU, folk, pop, valse, swing, bossa, fingerpick…).
- [x] **Dropdown préset** : sélection + section cible + bouton Appliquer dans l'éditeur rythme.
- [x] **Multi-mesures** : `pattern_lines` dans le modèle rhythm, rendu `|`-séparé dans la fiche mémo.
- [x] **`scripts/rhythm_utils.py`** : `normalize_rhythm_input`, `load_presets`, `get_preset_by_id`.
- [x] **234 tests — 227 passent (7 échecs pré-existants Supabase).**

## P13 — Pistes possibles

- [ ] Diagrammes d'accords en ASCII dans le mémo.
- [ ] LibreOffice headless comme moteur PDF principal (si installé).
- [ ] Améliorer la lisibilité de la fiche Mémo Guitare (PDF/DOCX).
- [ ] Drag-and-drop de position d'accord dans l'aperçu.

## À éviter (définitif)

- Scraping automatisé (fragile + légal).
- Web fetch automatique de sources de chords.
- Analyse de fichiers audio (MP3/WAV/OGG).
- Base de données (SQLite, Postgres, etc.).
- Framework frontend moderne (React, Vue, Svelte).
- Auth / déploiement web.
- Dépendances lourdes sans justification.
