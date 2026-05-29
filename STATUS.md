# STATUS.md

> Dernière mise à jour : 2026-05-25 (P10 — mode répétition, transposition, filtres bibliothèque, review_status, raccourcis clavier, export JSON fiche chanson)

## Phase actuelle

**Phase 10 — Mode répétition + ergonomie + bibliothèque**

L'éditeur local de songbook guitare/chant est maintenant utilisable en conditions de répétition/live :
2 vues plein écran sans éléments d'édition (paroles+accords et conducteur guitare), auto-scroll mains libres,
police ajustable, thème sombre, persistance localStorage. Transposition automatique (tous accords × demi-tons),
statuts de révision par chanson, filtres bibliothèque (tonalité, capo, statut), raccourcis clavier dans l'éditeur.

## Ce qui fonctionne

### Mode répétition — 2 vues plein écran (Phase 10 — 2026-05-25)

- `GET /song/<slug>/rehearsal/chords` → `rehearsal_chords.html` : paroles + accords, sans éditeurs
- `GET /song/<slug>/rehearsal/memo` → `rehearsal_memo.html` : conducteur guitare depuis `build_memo_lines`
- Contrôles : police ajustable (A−/A+), thème sombre, plein écran, auto-scroll
- Auto-scroll : `requestAnimationFrame`, vitesse réglable, start/stop (barre dédiée + Espace)
- Persistance localStorage : taille police, thème, vitesse scroll
- Raccourcis : `Espace` = pause · `+/-` = police · `F` = plein écran · `D` = thème · `L` = biblio

### Transposition automatique (Phase 10 — 2026-05-25)

- `scripts/transpose.py` : `transpose_chord()` + `transpose_song()`, gamme pratique
- Route `POST /song/<slug>/transpose`, borne −11..+11, backup automatique
- UI dans `song.html` : boutons ±1/±2, champ custom, backup avant transposition

### Statut de révision (Phase 10 — 2026-05-25)

- Champ optionnel JSON `review_status` : `"ok" | "to_review" | "draft"`
- Route `POST /song/<slug>/review-status` : mise à jour + backup automatique
- Badges visuels dans la bibliothèque + select inline AJAX par card

### Filtres bibliothèque (Phase 10 — 2026-05-25)

- Filtres JS locaux : tonalité (select), capo (sans/avec), statut révision
- `applyFilters()` combine texte + 3 filtres ; `resetFilters()` vide tout
- Badges : Validé/En attente, ✓ Prêt/⚠ À revoir/Brouillon, PDF ✓/PDF ✗
- Boutons "Paroles" et "Mémo" (mode répétition) ajoutés par card

### Raccourcis clavier song.html (Phase 10 — 2026-05-25)

- `S` = Sauvegarder et rafraîchir · `E` = Exporter PDFs · `L` = Bibliothèque · `F` = Plein écran
- Non déclenchés depuis INPUT/TEXTAREA/SELECT

### Export JSON depuis la fiche chanson (Phase 10 — 2026-05-25)

- Bouton "Télécharger JSON" dans la section Actions de `song.html`
- Réutilise la route existante `GET /song/<slug>/download-json`

### Backup automatique (Phase 9 — 2026-05-25)

- `_save_song()` crée un backup timestampé avant chaque écrasement
- Structure : `data/backups/<slug>/2026-05-25_14-32-10.json`
- Rotation automatique : 20 backups max par chanson
- Section "Historique / Backups" dans la fiche chanson avec bouton Restaurer
- Restauration : `POST /song/<slug>/restore/<filename>` → valide + régénère + redirige
- `scripts/backup.py` : `create_backup`, `list_backups`, `restore_backup`, `cleanup_old_backups`

### Confirmations avant suppressions (Phase 9 — 2026-05-25)

- Suppression d'accord (paroles ou instrumental) : `confirm('Supprimer cet accord ?')`
- Retrait d'une section de la séquence : `confirm('Retirer cette section de la séquence ?')`
- Restauration d'un backup : `confirm(...)` dans le formulaire

### Insertion d'accords dans les sections instrumentales (Phase 9 — 2026-05-25)

- Points d'insertion `+` visibles au survol de chaque `prev-grid-line`
- Support `performance_progression` (pp), `chord_grid` (cg), `summary_progression` (sp)
- Popup "Insérer un accord" dédié (`insert-instr-popup`)
- Route AJAX : `POST /song/<slug>/instr-chord/insert`
- Fonction `insert_instr_chord` dans `editor.py` (13 fonctions au total)

### Édition paroles inline (Phase 9 — 2026-05-25)

- Clic sur une ligne de paroles → input de texte inline
- Sauvegarde AJAX : `POST /song/<slug>/lyrics-at/update`
- Rafraîchissement partiel de l'aperçu
- Accords non déplacés : seul le texte change
- Fonction `update_lyrics_at` dans `editor.py`

### Recherche dans la bibliothèque (Phase 9 — 2026-05-25)

- Champ "Rechercher..." dans `/library`
- Filtrage live (JavaScript local) sur titre, artiste, album
- Compteur de résultats visible

### Export JSON depuis la bibliothèque (Phase 9 — 2026-05-25)

- Bouton "JSON" sur chaque card de `/library`
- Route `GET /song/<slug>/download-json`
- Headers corrects (`Content-Disposition: attachment`)

### PDF_EXPORT_DIR configurable (Phase 9 — 2026-05-25)

- `scripts/config.py` lit `.env.local` à la racine du projet
- Priorité : `.env.local` > variable d'environnement > valeur par défaut
- Pas de python-dotenv requis — parsing manuel minimal
- Comportement existant inchangé si `.env.local` absent

### Validation JSON renforcée (Phase 9 — 2026-05-25)

- `meta.slug` : regex `^[a-z0-9_-]+$` — espaces, `/`, `\`, majuscules refusés
- `section.id` : regex `^[a-zA-Z0-9_-]+$` — pas d'espaces ni de `/`
- Positions d'accords : ordre croissant vérifié, collisions exactes refusées
- Messages d'erreur précis affichés dans l'interface

### Tests Flask minimaux (Phase 9 — 2026-05-25)

- `tests/test_app.py` : 15 tests Flask (`app.test_client()`)
- Couvre : upload valide/invalide, bibliothèque, export JSON, backup, restore, export split, suppression accord, insertion instrumentale
- Nettoyage isolé avant/après chaque test

### Édition accords instrumentaux (Phase 8.3 — 2026-05-25)

- Sections `performance_progression`, `chord_grid`, `summary_progression` : accords cliquables
- Popup modifier / supprimer identique aux sections paroles
- Routes AJAX : `/song/<slug>/instr-chord/update`, `/song/<slug>/instr-chord/delete`

### Bouton global de sauvegarde (Phase 8.3 — 2026-05-25)

- "Sauvegarder et rafraîchir l'aperçu" → structure + rythme en un seul appel AJAX

### Bibliothèque web (Phase 8.2 — 2026-05-25)

- Route `/library` : tous les morceaux, infos complètes, liens PDF
- Actions : Éditer, Régénérer PDFs, Télécharger JSON, Supprimer

### Éditeur accords inline (Phase 8.1 — 2026-05-25)

- Clic sur accord → popup modifier/supprimer
- Survol ligne → points `+` pour insérer
- Sauvegarde AJAX → rafraîchissement partiel

## Chansons produites (9 morceaux, 18 PDFs dans Guitartabs/Chords)

- Moriarty — Jimmy
- Pink Floyd — Wish You Were Here
- Neil Young — Heart of Gold (midi)
- Zaho de Sagazan — La Symphonie des Éclairs
- Muse — Endlessly
- Cocoon — On My Way
- Eagles — Hotel California
- Gary Jules — Mad World
- Yodelice — Sunday with a Flu

## Architecture actuelle

```
Chords/
├── app.py                          ← interface web Flask
├── main.py                         ← CLI simplifié
├── requirements.txt
├── schema/song_schema.json         ← schéma JSON formel
├── templates/
│   ├── index.html                  ← accueil + upload
│   ├── song.html                   ← fiche chanson + éditeurs + aperçu HTML
│   ├── _preview.html               ← fragment aperçu interactif (inclus + AJAX)
│   ├── library.html                ← bibliothèque des morceaux
│   ├── rehearsal_chords.html       ← mode répétition : paroles + accords (P10)
│   └── rehearsal_memo.html         ← mode répétition : conducteur guitare (P10)
├── data/
│   ├── song_*.json                 ← JSON importés
│   └── backups/<slug>/             ← backups timestampés
├── output/                         ← DOCX + PDF + JSON générés
├── scripts/
│   ├── config.py                   ← chemins (+ .env.local pour PDF_EXPORT_DIR)
│   ├── validate_song_json.py       ← validation JSON (slug/IDs/positions)
│   ├── editor.py                   ← 13 fonctions d'édition JSON song
│   ├── backup.py                   ← backup/restore automatique
│   ├── generate_docx.py            ← génération DOCX + 2 PDFs
│   ├── memo.py                     ← logique fiche mémo guitare
│   ├── storage.py                  ← couche de stockage abstraite (local/supabase)
│   └── transpose.py                ← transposition automatique (P10)
├── tests/
│   ├── test_app.py                 ← 29 tests Flask (P9+P10)
│   ├── test_editor.py              ← 47 tests
│   ├── test_validate_json.py       ← 14 tests
│   ├── test_memo.py                ← 53 tests
│   ├── test_storage.py             ← tests storage
│   └── test_transpose.py           ← tests transposition
└── _archive/                       ← anciens scripts (collect, gemini, analyse, supabase, deploy)
```

**178 tests — 0 échec.**
