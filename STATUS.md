# STATUS.md

> Dernière mise à jour : 2026-05-25 (P9 — backup auto, restauration, édition paroles, insertion instrumentale, recherche bibliothèque, validation renforcée, tests Flask)

## Phase actuelle

**Phase 9 — Sécurité + confort d'édition + robustesse**

L'éditeur local de songbook guitare/chant est maintenant complet sur le plan de l'édition :
backup automatique à chaque sauvegarde, restauration en un clic, édition des paroles inline,
insertion d'accords dans les sections instrumentales, recherche dans la bibliothèque,
export JSON depuis la bibliothèque, PDF_EXPORT_DIR configurable, validation JSON renforcée,
confirmations avant suppressions destructives, et 15 tests Flask minimaux.

## Ce qui fonctionne

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

## Chansons produites (6 morceaux, 12 PDFs dans Guitartabs/Chords)

- Moriarty — Jimmy
- Pink Floyd — Wish You Were Here
- Neil Young — Heart of Gold
- Zaho de Sagazan — La Symphonie des Éclairs
- Muse — Endlessly
- Cocoon — On My Way

## Architecture actuelle

```
Chords/
├── app.py                          ← interface web Flask
├── main.py                         ← CLI simplifié
├── requirements.txt
├── song_template_with_rhythm.json  ← template de référence
├── schema/song_schema.json         ← schéma JSON formel
├── templates/
│   ├── index.html                  ← accueil + upload
│   ├── song.html                   ← fiche chanson + éditeurs + aperçu HTML
│   ├── _preview.html               ← fragment aperçu interactif (inclus + AJAX)
│   └── library.html                ← bibliothèque des morceaux
├── data/
│   ├── song_*.json                 ← JSON importés
│   └── backups/<slug>/             ← backups timestampés (P9)
├── output/                         ← DOCX + PDF + JSON générés
├── scripts/
│   ├── config.py                   ← chemins (+ .env.local pour PDF_EXPORT_DIR)
│   ├── validate_song_json.py       ← validation JSON (slug/IDs/positions)
│   ├── editor.py                   ← 13 fonctions d'édition JSON song
│   ├── backup.py                   ← backup/restore automatique (P9)
│   ├── generate_docx.py            ← génération DOCX + 2 PDFs
│   └── memo.py
├── tests/
│   ├── test_app.py                 ← 15 tests Flask (P9)
│   ├── test_editor.py              ← 47 tests
│   ├── test_validate_json.py       ← 14 tests
│   └── test_memo.py                ← 53 tests
└── _archive/                       ← anciens scripts
```

**129 tests — 0 échec.**
