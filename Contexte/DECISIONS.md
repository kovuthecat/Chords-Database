# DECISIONS.md

Journal des décisions produit et techniques.

---

## 2026-05-29 — P14 : Ajout accord mobile — mode explicite

### Décision

L'appui long (long-press) comme déclencheur d'insertion d'accord sur mobile est supprimé.
Il déclenchait la sélection native du texte au lieu d'ouvrir le popup d'ajout.

**Remplacement** : bouton "+ Accord" visible dans l'en-tête de la card aperçu.
- Quand actif : simple tap/clic sur une ligne de paroles ouvre le popup d'insertion.
- La zone paroles passe en `user-select: none` uniquement pendant ce mode (classe `.preview-editing-add-mode`).
- Après insertion : le mode se désactive automatiquement.
- Shift+clic desktop conservé (fonctionne en parallèle avec le mode bouton).

### Architecture

- Suppression de l'IIFE long-press (`touchstart` + `setTimeout` 600ms) dans `song.html`.
- Suppression de `_suppressLyricsClick` (variable utilisée uniquement par le long-press).
- Ajout de `_addChordMode` (bool) + `toggleAddChordMode()` dans `song.html`.
- `onLyricsClick` : condition `event.shiftKey || _addChordMode` (était `event.shiftKey` seul).
- `confirmInsertChord` : appelle `toggleAddChordMode()` avant `chordAjax` si mode actif.
- CSS : `.btn-add-chord`, `.btn-add-chord-active`, `#add-chord-hint`, `.preview-editing-add-mode .prev-lyrics-text`.
- `_preview.html` : `title` mis à jour (suppression de la mention "appui long").

### Pourquoi

L'appui long est non fiable sur iOS/Android : le navigateur déclenche la sélection native du texte avant que le timer JS ne s'exécute. Un mode explicite (bouton) est plus prévisible et ne nécessite aucun `preventDefault` global ni manipulation d'événements touch complexe.

### Conséquences

- Aucune modification du modèle JSON.
- Aucune modification backend ni des routes AJAX.
- Les tests existants ne sont pas affectés (logique JS non testée unitairement).

---

## 2026-05-29 — P12 : Édition accords + rythme

### Décisions

**Déplacement d'accord (← / →)**
- Popup édition accord : ajout d'un bloc "Position" avec boutons ← (delta -1) et → (delta +1).
- Champ numérique "Définir" pour fixer une position exacte.
- Deux nouvelles routes AJAX : `POST /chord-at/move` (delta) et `POST /chord-at/set-position` (position absolue).
- Deux nouvelles fonctions dans `editor.py` : `move_chord_at` et `set_chord_position`.
- Après déplacement, les accords sont re-triés par position (logique identique à `insert_chord_at`).
- Le popup se ferme après chaque action (approche simple — pas de ré-ancrage sur l'accord déplacé).

**Raccourcis clavier rythme**
- Touche `d` → `↓` et `u` → `↑` interceptées sur les inputs `.rhythm-pattern-input` (keydown → preventDefault + insertion).
- Implémentation purement JS dans `song.html`, aucune dépendance ajoutée.
- Seuls `d` et `u` sont interceptés (les caractères `x` et `.` sont déjà directement saisissables).

**Bibliothèque de présets**
- `static/rhythm_patterns.json` : 8 présets (DU straight, folk DUUDU, pop DDUUDU, valse, swing, bossa, Travis, arpège).
- Chargé via `fetch('/static/rhythm_patterns.json')` au chargement de `song.html` pour peupler le dropdown.
- Dropdown "préset + section cible + Appliquer" pré-remplit pattern/feel sans sauvegarder.
- `scripts/rhythm_utils.py` : `normalize_rhythm_input`, `load_presets`, `get_preset_by_id` (Python).

**Multi-mesures (modèle de données)**
- Champ optionnel `pattern_lines: list[str]` ajouté au modèle rhythm (backward compatible).
- `memo.py/_build_rhythm_hint` : si `pattern_lines` présent → join avec ` | `, sinon `pattern` comme avant.
- Pas d'UI d'édition multi-mesures dans P12 (saisie JSON directe ou future session).
- Validation JSON : champs optionnels non vérifiés (pas de schéma strict sur rhythm).

**Tests**
- 11 nouveaux tests dans `test_editor.py` (TestMoveChordAt × 6, TestSetChordPosition × 5).
- 20 nouveaux tests dans `test_rhythm.py` (normalize, presets, _build_rhythm_hint, intégration).
- Total : 234 tests, 227 passent (7 échecs Supabase inchangés).

### Conséquences
- `editor.py` passe de 13 à 15 fonctions.
- `app.py` : 2 nouvelles routes AJAX (cohérentes avec le pattern existant).
- Les JSON existants ne sont pas affectés (nouveaux champs optionnels).

---

## 2026-05-29 — P11 : Simplification interface

### Décisions

**Page d'accueil → bibliothèque**
- `GET /` redirige vers `/library` (redirect Flask).
- `GET /add` → `index.html` (formulaire d'upload, ancienne page d'accueil).
- La bibliothèque est maintenant le point d'entrée naturel de l'application.

**Navigation par icônes**
- Headers de `library.html` et `song.html` : emojis comme icônes légères (pas de dépendance externe).
- `library.html` : "📚 Bibliothèque" + bouton "➕ Ajouter" à droite.
- `song.html` : "📚 Biblio · ➕ · 🎵 · 🎸 · 📄 (si PDF dispo)" — liens contextuels à la chanson courante.
- Bloc "Mode répétition" standalone retiré de `song.html` (redondant avec la nav).

**Cards bibliothèque simplifiées**
- Actions primaires : ✏️ Éditer / 🎵 Paroles (mode répétition) / 📄 PDF Paroles / 🎸 PDF Mémo.
- Bloc `<details class="song-advanced">` "Options avancées" par card :
  - 🎸 Mémo répétition
  - ⬆ Mettre à jour les fiches (export-split)
  - ⬇ JSON
  - 🗑 Supprimer
- Statut révision (select AJAX) reste visible en primaire.
- Badge validation workflow (`user_validated`/`pending`) conservé dans song-info.

**Transposition améliorée (song.html)**
- Tonalité actuelle et capo affichés en tête de la carte.
- Boutons -2/-1/+1/+2 : sélectionnent la valeur dans le champ custom (ne déclenchent plus directement).
- Aperçu "Tonalité estimée : Gm (+3 demi-tons)" mis à jour en temps réel (JS : `estimateKey`).
- `estimateKey` en JS : miroir de `_PRACTICAL` + `_ENHARMONIC` de `scripts/transpose.py`.
- Bouton unique "Appliquer" : confirm enrichie (inclut la tonalité estimée).
- Route `/song/<slug>/transpose` inchangée.

**Éditeur de remplacement d'accord global**
- Retiré de la position principale dans `song.html`.
- Déplacé dans "Options avancées" (`<details>`) de la section Actions.
- L'édition inline dans l'aperçu couvre l'essentiel des cas d'usage.

**Labels nettoyés**
- "Valider et exporter 2 PDFs" → "Exporter les fiches" (song.html).
- "PDFs" (library) → "⬆ Mettre à jour les fiches" (Options avancées).
- Navigation éditeurs : "Accords" retiré (l'éditeur est en Options avancées).

### Pourquoi

L'interface après P10 avait trop d'actions au premier plan. L'usage courant (répétition, lecture PDF)
ne nécessite pas l'accès permanent aux outils techniques (JSON, regen PDFs, remplacement global).
La bibliothèque est la destination principale — autant en faire la page d'accueil.

### Conséquences

- Route `/` change de comportement (redirect) — aucun test ne la couvrait.
- Route `/add` créée (nouvelle).
- Aucune modification backend (routes AJAX, logique Python, scripts) — uniquement UI.
- 196 tests passent sur 203 ; les 7 échecs sont pré-existants (backend Supabase en environnement de test).

---

## 2026-05-25 — P10 : Mode répétition + ergonomie + bibliothèque

### Décisions

**Mode répétition — 2 vues plein écran**
- `GET /song/<slug>/rehearsal/chords` → `rehearsal_chords.html` : paroles + accords, sans éditeurs.
- `GET /song/<slug>/rehearsal/memo` → `rehearsal_memo.html` : conducteur guitare, depuis `build_memo_lines`.
- Contrôles : police ajustable (A−/A+), thème sombre, plein écran, auto-scroll.
- Auto-scroll : `requestAnimationFrame`, vitesse réglable, start/stop (barre dédiée + barre Espace).
- Persistance localStorage : taille police, thème, vitesse scroll.
- Raccourcis : `Espace` = pause scroll · `+/-` = police · `F` = plein écran · `D` = thème · `L` = biblio.
- Lien "Mode répétition" ajouté dans `song.html` (avant la navigation éditeurs).

**Raccourcis clavier song.html**
- `S` = Sauvegarder et rafraîchir · `E` = Exporter PDFs · `L` = Bibliothèque · `F` = Plein écran.
- Non déclenchés depuis INPUT/TEXTAREA/SELECT.

**Export JSON depuis la fiche chanson**
- Bouton "Télécharger JSON" ajouté dans la section Actions de `song.html`.
- Réutilise la route existante `GET /song/<slug>/download-json`.

**Statut de révision (`review_status`)**
- Champ optionnel JSON au niveau racine : `"review_status": "ok" | "to_review" | "draft"`.
- Route `POST /song/<slug>/review-status` : met à jour le champ, backup automatique.
- Badges visuels dans la bibliothèque + select inline AJAX par card.
- `_list_songs()` inclut `review_status`.

**Bibliothèque — filtres et badges**
- Filtres JS locaux : tonalité (select), capo (sans/avec), statut révision.
- `applyFilters()` combine texte + 3 filtres ; `resetFilters()` vide tout.
- Nouveaux `data-key`, `data-capo`, `data-review` sur chaque `.song-card`.
- Badges : Validé/En attente, ✓ Prêt/⚠ À revoir/Brouillon, PDF ✓/PDF ✗.
- Boutons "Paroles" et "Mémo" (mode répétition) ajoutés par card.
- `library()` route passe `keys` (liste triée des tonalités) au template.

**Transposition automatique (déjà livré dans sprint précédent)**
- `scripts/transpose.py` : `transpose_chord()` + `transpose_song()`, gamme pratique.
- Route `POST /song/<slug>/transpose`, borne −11..+11, backup automatique.
- UI carte dans `song.html` : boutons rapides ±1/±2, champ custom.

### Pourquoi

Usage réel répétition/live : besoin d'une vue propre sans les éléments d'édition, avec auto-scroll mains libres, police agrandie et thème sombre pour les conditions de scène.

### Conséquences

- 2 nouveaux templates : `rehearsal_chords.html`, `rehearsal_memo.html`.
- 3 nouvelles routes Flask : rehearsal/chords, rehearsal/memo, review-status.
- 14 nouveaux tests Flask (TestRepetition, TestReviewStatus, TestTransposeRoute).
- **178 tests au total — 0 régression.**
- Le projet est maintenant décrit comme : **éditeur local de songbook guitare/chant avec mode répétition**.

---

## 2026-05-25 — P9 : Sécurité + confort d'édition + robustesse

### Décisions

**Backup automatique JSON**
- `_save_song()` appelle `create_backup()` avant chaque écrasement.
- Structure : `data/backups/<slug>/<timestamp>.json` (20 max, rotation automatique).
- `scripts/backup.py` : `create_backup`, `list_backups`, `restore_backup`, `cleanup_old_backups`.
- Restauration : `POST /song/<slug>/restore/<filename>` — valide le backup, sauvegarde l'actuel, régénère.

**Confirmations avant suppressions**
- `confirm('Supprimer cet accord ?')` dans `confirmDeleteChord()`.
- `confirm('Retirer cette section ?')` dans `removeRow()`.
- `confirm(...)` sur le formulaire de restauration.

**Insertion d'accords dans les sections instrumentales**
- Points `+` visibles au survol de chaque `prev-grid-line` (CSS opacity).
- Popup `insert-instr-popup` dédié.
- Route `POST /song/<slug>/instr-chord/insert`.
- `insert_instr_chord(song, section_id, instr_type, insert_at, chord, ppi, li)` dans `editor.py`.

**Édition paroles inline**
- Clic sur `.prev-lyrics-text` → input inline en remplacement.
- Sauvegarde AJAX : `POST /song/<slug>/lyrics-at/update`.
- Accords non déplacés : seul le champ `lyrics` change.
- `update_lyrics_at(song, section_id, line_index, new_lyrics)` dans `editor.py`.

**Recherche dans la bibliothèque**
- Champ texte dans `/library`, JavaScript local, filtrage sur `data-title`/`data-artist`/`data-album`.
- Aucune route backend supplémentaire.

**Export JSON**
- Route `GET /song/<slug>/download-json` → `send_file` avec `as_attachment=True`.
- Bouton "JSON" sur chaque card de la bibliothèque.

**PDF_EXPORT_DIR configurable**
- `config.py` : lecture de `.env.local` (parsing manuel, sans python-dotenv).
- Priorité : `.env.local` > `os.environ["PDF_EXPORT_DIR"]` > valeur par défaut.

**Validation JSON renforcée**
- `meta.slug` : `^[a-z0-9_-]+$` — refus des espaces, `/`, `\`, majuscules.
- `section.id` : `^[a-zA-Z0-9_-]+$`.
- Positions d'accords : ordre croissant vérifié, collisions exactes refusées.

**Tests Flask minimaux**
- `tests/test_app.py` : 15 tests `app.test_client()`.
- Isolation par slug de test dédié + nettoyage `autouse=True`.

### Pourquoi

Confort d'utilisation quotidienne : les corrections d'erreurs de sauvegarde nécessitaient jusqu'ici une intervention manuelle dans le système de fichiers. Le backup automatique élimine ce risque. L'insertion instrumentale et l'édition de paroles complètent la promesse d'édition 100% en navigateur.

### Conséquences

- `editor.py` : 13 fonctions (était 11).
- `scripts/backup.py` créé (nouveau module).
- `tests/test_app.py` créé (15 tests Flask).
- 129 tests au total — 0 régression.
- `CLAUDE.md` : décrire comme "éditeur local de songbook" (fait).

---

## 2026-05-25 — P8.3 : Édition des accords dans les sections instrumentales

### Décision

Les accords des sections instrumentales (`performance_progression`, `chord_grid`,
`summary_progression`) sont désormais affichés comme des spans cliquables dans l'aperçu HTML,
avec le même popup modifier/supprimer que les sections avec paroles.

### Architecture

- `templates/_preview.html` : rendu chord-by-chord avec classe `.instr-chord` (position:static)
  au lieu du texte brut précédent. Attributs `data-instr-type` (pp/cg/sp), `data-section`,
  `data-ppi`, `data-li`, `data-ci`.
- Filtre Jinja2 `parse_chord_grid` dans `app.py` : parse `chord_grid` multi-lignes en
  `[{li, chords: [{ci, chord}]}]` avec indices de lignes réels pour rebuildage fidèle.
- `scripts/editor.py` : `update_instr_chord` et `delete_instr_chord` (+ helpers internes
  `_cg_lines`, `_parse_cg_line`, `_build_cg_line`). Recalculent `chords_used` après chaque op.
- Routes AJAX : `/song/<slug>/instr-chord/update`, `/song/<slug>/instr-chord/delete`
- JS `song.html` : `confirmEditChord` / `confirmDeleteChord` vérifient `_editTarget.dataset.instrType`
  et routent vers l'endpoint approprié.

### Pourquoi

Les sections instrumentales (intro, solo, interlude) contiennent des accords qui nécessitent
parfois des corrections après génération. L'absence d'interactivité les rendait inaccessibles
sans passer par l'édition manuelle du JSON.

### Conséquences

- `editor.py` : 11 fonctions (était 9).
- L'insertion d'accord dans les sections instrumentales n'est pas encore supportée (hors scope P8.3).

---

## 2026-05-25 — P8.3 : Bouton global de sauvegarde structure + rythme

### Décision

Les boutons séparés "Sauvegarder la structure" et "Sauvegarder les rythmes" sont remplacés
par un seul bouton AJAX "Sauvegarder et rafraîchir l'aperçu" commun aux deux éditeurs.

### Architecture

- Route `POST /song/<slug>/save-all` : reçoit les données de `form-structure` + `form-rhythm`
  en une seule requête, applique `apply_structure_edits` puis `apply_all_rhythm_edits`, sauvegarde.
- JS `saveAll()` : sérialise la séquence, collecte les deux formulaires via `FormData`,
  POST AJAX, rafraîchit l'aperçu en cas de succès.
- Les formulaires ont `onsubmit="return false"` pour bloquer les submits accidentels.

### Pourquoi

L'utilisateur modifiait souvent structure ET rythme dans le même passage de corrections.
Deux boutons séparés forçaient deux soumissions (deux rechargements). Le bouton unique
évite la friction et rafraîchit l'aperçu sans rechargement.

---

## 2026-05-25 — P8.3 : Suppression d'une chanson depuis la bibliothèque

### Décision

La bibliothèque permet de supprimer un morceau entier avec tous ses fichiers liés.

### Architecture

- Route `POST /song/<slug>/delete` : supprime `data/song_<slug>.json`,
  `output/song_<slug>.*` (DOCX, PDF, JSON), PDFs exportés dans `PDF_EXPORT_DIR`.
- Bouton "Supprimer" rouge dans chaque card de `library.html`, avec `confirm()` JS.
- Redirection vers `/library` après suppression.

### Pourquoi

Permettre de nettoyer la bibliothèque sans manipulation manuelle dans l'explorateur.
Une chanson ratée ou un doublon encombre l'index et laisse des fichiers orphelins dans `PDF_EXPORT_DIR`.

### Conséquences

- Les PDFs exportés dans `PDF_EXPORT_DIR` (hors du repo) sont aussi supprimés — action irréversible.
  D'où le `confirm()` obligatoire.

---

## 2026-05-25 — P8.3 : _save_song écrit dans data/ et output/

### Décision

`_save_song()` dans `app.py` écrit le JSON dans `data/song_<slug>.json` ET dans
`output/song_<slug>.json` à chaque sauvegarde.

### Pourquoi

Le dossier `output/` regroupe tous les artefacts générés pour un morceau (DOCX, PDF, JSON).
Avoir le JSON à jour dans `output/` facilite l'archivage ou l'export manuel sans avoir à
naviguer entre deux dossiers.

---

## 2026-05-25 — P8.3 : Fix nettoyage PDF "Comprendre le Morceau" résiduel

### Décision

`generate_split_pdf()` appelle `_cleanup_deprecated_pdfs(song)` avant chaque export.
Cette fonction supprime `Artiste - Titre - Comprendre le Morceau.pdf` dans `PDF_EXPORT_DIR`
si le fichier existe encore depuis une génération antérieure à P8.2.

### Pourquoi

Après la suppression de la 3e fiche (P8.2), les anciens PDFs restaient sur disque.
L'utilisateur les voyait encore dans `PDF_EXPORT_DIR` et croyait qu'ils avaient été régénérés.

---

## 2026-05-25 — P8.2 : Bibliothèque web locale des morceaux

### Décision

Ajout d'une page `/library` dans l'interface Flask présentant tous les morceaux disponibles
dans `data/`, avec consultation directe des PDFs exportés et actions de réédition/régénération.

### Architecture

- Route `/library` dans `app.py` → `templates/library.html`
- Route `/export/<filename>` → sert les fichiers de `PDF_EXPORT_DIR`
- `_list_songs()` enrichi : album, key, capo, tempo, chemin PDF chords/memo, date modification
- Bibliothèque charge les données directement depuis `data/song_*.json` (pas de base de données)

### Actions disponibles depuis la bibliothèque

- **Fiches PDF** : liens directs vers Paroles & Accords + Mémo Guitare (griser si absent)
- **Éditer** : lien vers `/song/<slug>` (éditeur inline + éditeurs accords/structure/rythme)
- **Régénérer PDFs** : bouton `export-split` embarqué dans la card

### Pourquoi

Éviter de naviguer manuellement dans `PDF_EXPORT_DIR` ou de passer par `/` pour accéder
aux morceaux déjà traités. La bibliothèque est le point d'entrée naturel pour l'usage courant.

---

## 2026-05-25 — P8.2 : Suppression de la fiche musicale / page 3

### Décision

La fiche "Comprendre le Morceau" (page 3) est retirée du workflow standard.
`scripts/analysis.py` est archivé dans `_archive/`. `tests/test_analysis.py` est supprimé.

### Pourquoi

- Hors périmètre usage répétition/live : les guitaristes/chanteurs n'ont pas besoin
  d'analyse harmonique pendant la préparation d'un set.
- Recentrage sur : chant, guitare, structure, rythme.
- Simplification du pipeline (moins de dépendances, moins de surface).

### Conséquences

- `generate_docx.py` : suppression de `add_analysis_page_docx`, `_add_analysis_page_pdf`,
  `generate_learning_only`, `"learning"` dans `_PART_LABELS` et `_generate_split_pdf_reportlab`.
- Export split : 2 PDFs seulement (Paroles & Accords + Mémo Guitare).
- `_PART_LABELS` : plus de clé `"learning"`.
- `app.py` : `exported` message mis à jour ("2 PDFs").
- `song.html` : liste des PDFs réduite à 2.
- Les champs JSON `harmonic_analysis`, `confidence`, `key`, `key_mode` **restent compatibles** —
  non supprimés du format d'entrée, juste non utilisés pour la génération.
- `analysis.py` archivé dans `_archive/` — réactivable si besoin futur.

---

## 2026-05-25 — P8.1 : Fix — priorité performance_progression dans DOCX/PDF page 1

### Décision

`generate_docx.py` : pour les sections instrumentales, vérifier `performance_progression` en premier,
avant `chord_grid`. Même priorité que la page 2 (mémo) et l'aperçu HTML.

### Pourquoi

La page 1 affichait le `chord_grid` brut (ex : `| Em7 | D | Em | Am |`) même quand
`performance_progression` contait des regroupements avec répétitions (ex : `Em7 D Em ×2`).
Incohérence entre l'aperçu HTML (correct) et le DOCX/PDF téléchargé (incomplet).

### Conséquences

- `render_section` (DOCX python-docx) : `perf_explicit` vérifié avant `chord_grid`.
- Section reportlab (PDF page 1) : même fix en parallèle.
- Aucune modification du format JSON — `performance_progression` était déjà le champ de référence.

---

## 2026-05-25 — P8.1 : Éditeur accords inline dans l'aperçu HTML

### Décision

L'aperçu PDF (iframe) est remplacé par un aperçu HTML interactif dans la fiche chanson.
Les accords sont éditables en place, sans rechargement de page.

### Architecture

- `templates/_preview.html` : fragment Jinja2 inclus dans `song.html` ET servi par la route AJAX
  `/song/<slug>/preview-html`. Un seul template pour les deux usages.
- `ch` units CSS pour le positionnement absolu des accords au-dessus des paroles
  (1 `ch` = 1 caractère monospace = correspond à l'offset `position` dans le JSON).
- Popups `position: fixed` (pas `absolute`) → les coordonnées `getBoundingClientRect()` sont
  directement utilisables sans correction scroll.
- Filtre Jinja2 `word_positions` : split sur espaces + tracking offset → `[{word, pos}]`.
- `pointer-events: none` sur `.prev-inserts` + `pointer-events: all` sur `.insert-pt`
  pour que les `+` n'interceptent pas les clics sur les paroles.

### Nouvelles fonctions editor.py

- `delete_chord_at(song, section_id, line_index, chord_index)` : supprime un accord ciblé
- `update_chord_at(song, section_id, line_index, chord_index, new_chord)` : modifie un accord ciblé
- `insert_chord_at(song, section_id, line_index, chord, position)` : insère + trie par position

### Nouvelles routes app.py

| Route | Méthode | Rôle |
|---|---|---|
| `/song/<slug>/preview-html` | GET | Fragment HTML aperçu (AJAX) |
| `/song/<slug>/chord-at/update` | POST | Modifier un accord ciblé |
| `/song/<slug>/chord-at/delete` | POST | Supprimer un accord ciblé |
| `/song/<slug>/chord-at/insert` | POST | Insérer un accord à une position |

### Pourquoi

Éviter l'aller-retour JSON → éditeur externe → réupload pour une correction simple d'accord.
L'édition directe dans le preview couvre 80% des cas d'ajustement post-génération.

### Conséquences

- `song.html` restructuré : aperçu HTML à la place de l'iframe PDF (PDF déplacé dans `<details>`).
- `tests/test_editor.py` : +15 tests (3 nouvelles classes × 5 tests chacune), total 157.

---

## 2026-05-25 — P8 : Pivot vers interface web locale — JSON externe comme entrée unique

### Décision

Le workflow est simplifié autour d'un JSON externe finalisé comme **seule entrée**.
Le projet ne génère plus, n'extrait plus, ne reconstruit plus les données chanson.

1. L'utilisateur crée le JSON en dehors du projet (ex: Claude AI avec le prompt dédié).
2. L'utilisateur uploade le JSON dans l'interface web Flask (`python app.py`).
3. Le projet valide, génère DOCX + aperçu PDF.
4. L'utilisateur valide dans le navigateur.
5. Export 3 PDFs séparés dans `PDF_EXPORT_DIR`.

### Pourquoi

- L'ancien workflow (PDF → Gemini → reconstruct → validate_harmony → display_validation → DOCX)
  était trop complexe pour un usage personnel.
- Gemini API instable, Claude Code plus efficace pour la construction du JSON.
- La logique métier (DOCX, PDF, mémo, analyse) est bonne — seule l'interface d'entrée change.
- Une interface web locale est plus ergonomique que le terminal pour la validation.

### Conséquences

- `app.py` créé (Flask, port 5000).
- `scripts/validate_song_json.py` créé (validation entrante).
- `main.py` simplifié (CLI JSON → DOCX uniquement, plus d'orchestration multi-étapes).
- Scripts archivés dans `_archive/` : `collect.py`, `gemini_extract.py`, `gemini_client.py`,
  `reconstruct.py`, `display_validation.py`, `validate_harmony.py`.
- Tests obsolètes supprimés : `test_collect.py`, `test_harmony.py`, `test_reference_songs.py`,
  `test_gemini_extract.py`.
- `song_template_with_rhythm.json` devient le format d'entrée officiel.
- `schema/song_schema.json` mis à jour en JSON Schema formel.

---

## 2026-05-24 — P7 : Abandon Gemini API — Claude Code comme extracteur

### Décision

`gemini_extract.py` ne fonctionne pas en pratique (quota, erreurs API). Le pipeline
d'extraction bascule sur **Claude Code en appui manuel** :

1. L'utilisateur fournit un PDF + URL(s) validées dans la conversation.
2. Claude Code lit le PDF directement (capacité multimodale) + WebFetch les URLs.
3. Claude Code construit le JSON `data/song_<slug>.json` manuellement.
4. La pipeline aval (reconstruct → validate_harmony → display_validation → generate_docx) est inchangée.

`gemini_extract.py` reste dans le repo mais n'est plus le workflow principal.

### Pourquoi

- L'API Gemini ne répond pas de façon fiable dans ce contexte.
- Claude Code peut lire les PDFs directement — même résultat, sans dépendance externe.
- Le processus reste entièrement sous contrôle utilisateur (mêmes garanties légales).

### Conséquences

- `PROCESS.md` créé : guide de référence rapide pour Claude Code.
- `_extraction_method: "manual_pdf"` dans les nouveaux JSON.
- `gemini_extract.py` conservé (non supprimé) — réactivable si l'API devient stable.
- Heart of Gold rebuild : corrections structurelles depuis PDF BAC (intro, refrain x2, Em7).

---

## 2026-05-24 — P6.1 : URLs fournies par l'utilisateur comme source complémentaire

### Décision

Clarification de P6 : les URLs fournies **explicitement par l'utilisateur** sont acceptées
comme source complémentaire, en plus des PDFs. Le contenu est récupéré par le script et
transmis à Gemini comme contexte textuel supplémentaire.

La distinction fondamentale avec ce qui est interdit reste :
- **Interdit** : le pipeline cherche lui-même des sources sur le web (automatique, non sollicité).
- **Autorisé** : l'utilisateur fournit une URL qu'il a choisie (`--url`), le script la récupère.

### Sources acceptées (mis à jour)

- PDF (tablature, fiche chord, partition) — via Gemini
- URL fournie par l'utilisateur (`--url`) — contenu transmis à Gemini comme contexte
- MIDI officiel ou fourni — extraction légère (tempo, signature) via `mido`
- Texte brut copier-coller — via `collect.py --ingest` (inchangé)

### Toujours interdit

- Recherche web automatique (le pipeline ne cherche jamais de sources par lui-même)
- Scraping non sollicité de Songsterr / Ultimate Guitar / La Boîte à Chansons
- Tout workflow où le projet choisit lui-même les sources

### Conséquences

- `scripts/gemini_extract.py` : `--url` (répétable), `_fetch_url_text()`, `url_sources` dans la signature.
- Les URLs apparaissent dans `sources[]` avec `type: "url"` dans le JSON.
- `TestNoWebScraping` : la règle testée reste valide (pas d'appel automatique).

---

## 2026-05-24 — P6 : Bascule vers pipeline PDF-first via Gemini

### Décision

Le projet abandonne le workflow de recherche web automatique (requêtes vers Songsterr,
Ultimate Guitar, La Boîte à Chansons, WebFetch) et bascule vers un pipeline basé
exclusivement sur des sources fournies par l'utilisateur : PDF et/ou MIDI.

Gemini (via `scripts/gemini_extract.py`) extrait les informations structurées depuis
les fichiers fournis et produit un JSON compatible avec le pipeline existant.

### Sources acceptées désormais

- PDF (tablature, fiche chord, partition) — via Gemini
- MIDI officiel ou fourni — extraction légère (tempo, signature) via `mido`
- Texte brut copier-coller — via `collect.py --ingest` (inchangé)

### Sources supprimées

- Recherche web automatique (WebSearch, WebFetch)
- Scraping Songsterr / Ultimate Guitar / La Boîte à Chansons
- Tout workflow où le projet cherchait lui-même les sources

### Raison du choix

1. **Légal** : éviter tout accès automatisé à des sources protégées.
2. **Fiabilité** : Gemini sur PDF fourni est plus fiable qu'un parser de page web fragile.
3. **Simplicité** : l'utilisateur contrôle totalement les sources — pas de surprise.
4. **Qualité** : un PDF officiel ou de qualité donne de meilleurs résultats qu'un scrape.

### Conséquences

- `scripts/gemini_extract.py` créé — module d'extraction principal.
- `main.py` refactorisé : `--pdf`, `--midi`, `--json`, `--list`.
- `collect.py` : `print_search_queries()` supprimée, toutes références web retirées.
- Ancien workflow `"Titre" "Artiste"` → message d'erreur clair avec guidance vers `--pdf`.
- `requirements.txt` : `google-genai>=1.0.0` (extraction), `mido>=1.3.0` (MIDI, optionnel).
- `tests/test_gemini_extract.py` : 30+ tests, dont une classe `TestNoWebScraping`.
- Pipeline existant (reconstruct → validate → docx) inchangé.
- JSON des chansons existantes restent générables sans modification.

---

## 2026-05-24 — Configuration Gemini (module optionnel)

### Décision

Ajout d'une configuration Gemini locale dans Chords via `.env.local` (`GEMINI_API_KEY`) et un module `scripts/gemini_client.py` minimal. Gemini n'est pas encore intégré au pipeline de génération.

### Raison du choix

Préparer une intégration future (assistance à la reconstruction, complétion harmonique) sans modifier le pipeline existant et sans coupler Chords au projet MYO — même clé API, projets totalement indépendants.

### Conséquences

- `.env.example` : template versionné sans secret.
- `.env.local` : clé réelle, exclue par `.gitignore` (`.env` et `.env.local` ajoutés).
- `scripts/gemini_client.py` : lecture clé, chargement `.env.local` sans dépendance python-dotenv, init SDK, commande `--test`.
- `requirements.txt` : `google-generativeai>=0.8.0` commenté (optionnel — décommenter pour activer).
- Pipeline existant inchangé.

---

## 2026-05-23 — P5 : Export PDF split (3 fichiers séparés)

### Décision

Chaque chanson produit 3 PDFs séparés dans `PDF_EXPORT_DIR` (Guitartabs/Chords) :
- `song_<slug>_paroles_chords.pdf`
- `song_<slug>_memo_guitare.pdf`
- `song_<slug>_comprendre_morceau.pdf`

Le moteur PDF principal reste reportlab (LibreOffice non installé sur le poste). La tentative LibreOffice est conservée en priorité pour un meilleur rendu si LibreOffice est installé à l'avenir.

### Raison du choix

Permettre l'usage en contexte de répétition : impression de la page chords seule, ou consultation rapide du conducteur guitare sans avoir le document complet.

### Conséquences

- `generate_pdf()` : paramètre `parts=None` — filtre les pages à inclure (pas de réécriture majeure).
- `add_memo_page_docx()`, `add_analysis_page_docx()`, `_add_memo_page_pdf()`, `_add_analysis_page_pdf()` : paramètre `page_break=True` — permet rendu partiel sans saut de page initial.
- `main()` converti de `sys.argv` brut vers `argparse` pour supporter `--split-pdf` et `--part`.

---

## 2026-05-23 — P4 : Conducteur guitare — fiche mémo multi-lignes

### Décision

La page 2 (fiche mémo) affiche désormais plusieurs lignes par section quand la structure le nécessite. L'extraction utilise `_extract_performance_lines()` avec priorité : `performance_progression` > `summary_progression` > `chord_grid` > lignes paroles.

La détection de motif (`_find_repeat_pattern`) conserve les doublons d'accords : `Am F G Am (x4)` ne se simplifie pas en `Am F G (x4)`.

### Raison du choix

L'ancien `_extract_progression` n'affichait que la première ligne et dédupliquait les accords, rendant le conducteur inutilisable pour des sections complexes (multi-lignes) ou des sections avec patterns répétés.

### Conséquences

- `memo.py` : 3 nouvelles fonctions, champ `"lines"` dans `build_memo_lines()`.
- `"progression"` conservé pour backward compatibility.
- Champ JSON optionnel `performance_progression` permettant de surcharger la détection automatique.

---

## 2026-05-23 — P4 : Page 3 — COMPRENDRE LE MORCEAU

### Décision

La page 3 remplace "FICHE DE SYNTHÈSE MUSICALE" par "COMPRENDRE LE MORCEAU" avec 5 sections : Idée principale, Boucles à retenir, Couleur du morceau, Comment mémoriser, Conseils guitare/chant.

### Raison du choix

L'ancienne page affichait des degrés romains section par section — utile pour l'analyse théorique mais peu lisible pour un usage pratique au quotidien. La nouvelle format donne immédiatement les informations exploitables.

### Conséquences

- `analysis.py` : 4 nouvelles fonctions. Anciens champs (`mood`, `sections`, `memory_notes`, `guitar_tips`) conservés dans `build_musical_analysis()`.
- `generate_docx.py` / `display_validation.py` : nouveau rendu.

---

## 2026-05-23 — P3 : Album dans le bloc en-tête DOCX/PDF

### Décision

Le champ `meta.album` est optionnel dans le JSON. S'il est renseigné, il s'affiche en italique entre l'artiste et la ligne de métadonnées (tonalité, capo, tempo) dans le DOCX et le PDF.

### Raison du choix

Enrichit l'en-tête sans surcharger les fiches. Compatibilité totale avec les anciens JSON (champ absent = rien affiché).

### Conséquences

- `generate_docx.py` : `add_title_block()` et `generate_pdf()` testent `meta.get("album")`.
- `song_schema.json` : champ `album` documenté avec note `_album_doc`.
- Format suggéré : `"Nom de l'album (année)"`.

---

## 2026-05-23 — P3 : Mode --list dans main.py

### Décision

`python main.py --list` affiche un tableau de toutes les chansons présentes dans `data/`, avec titre/artiste, slug, statut de validation, score de confiance et présence du DOCX.

### Raison du choix

Permet un aperçu rapide sans ouvrir les JSON ni chercher dans `output/`. Workflow CLI uniquement — pas de base de données, pas d'interface.

### Conséquences

- `main.py` : `title` et `artist` deviennent `nargs="?"` pour permettre l'usage de `--list` seul.
- Lecture directe des JSON dans `DATA_DIR` à chaque appel (pas de cache).

---

## 2026-05-23 — P3 : Suppression du doublon "accords barrés" dans analysis.py

### Décision

Le bloc qui ajoutait `"Accords barrés possibles : ... — soigner le barré."` a été supprimé. Seul le second bloc (plus complet, ajoutant aussi les accords ouverts) est conservé.

### Raison du choix

Le premier bloc était un résidu d'une version antérieure. Il produisait deux conseils identiques sur les accords barrés dans la fiche de synthèse musicale.

---

## 2026-05-23 — P2 : STRICT_MODE dans analysis.py

### Décision

`STRICT_MODE = True` activé par défaut dans `analysis.py`.

### Raison du choix

Réduire les analyses spéculatives et les affirmations pédagogiques trop affirmatives.
En STRICT_MODE : descriptions factuelles (`describe_mood`), progressions nommées uniquement
si ≥ 4 degrés connus, observations structurelles sans qualificatifs subjectifs.

### Conséquences

- La fiche page 3 est plus sobre mais plus fiable.
- Désactivable pour une analyse pédagogique plus riche (changer `STRICT_MODE = False`).

---

## 2026-05-23 — P2 : Tests unitaires et corpus de référence

### Décision

Création de `tests/` avec 5 fichiers de tests pytest et `tests/reference_songs/` avec 5 chansons.

### Raison du choix

Permettre la détection rapide de régressions lors de modifications du parser, de la logique harmonique
ou du rendu. Les chansons de référence couvrent des cas variés : accords simples, slash chords,
sections complexes, accords enrichis, FR et EN.

### Conséquences

- `pytest` lance 155 tests en < 0.5s.
- Toute modification du parser doit maintenir le passage des tests de référence.

---

## 2026-05-23 — P2 : Score de confiance global visible

### Décision

Le score de confiance global est affiché en tête du brouillon de validation (terminal)
et sur la page 3 du DOCX.

### Raison du choix

Aider l'utilisateur à calibrer son niveau de vérification avant de valider.
Score < 60% → avertissement clair avec guidage spécifique.

### Conséquences

- `display_validation.py` : bloc "SCORE DE CONFIANCE GLOBAL" en tête, avec barre visuelle.
- `generate_docx.py` : section "Confiance" ajoutée en début de la page 3.

---

## 2026-05-23 — P2 : Validation structurelle heuristique

### Décision

`reconstruct.py` appelle `check_structural_completeness()` pour détecter les sections
attendues manquantes (intro, refrain, couplet) et les sections vides.

### Raison du choix

Améliorer la fiabilité du brouillon de validation sans construire un moteur complexe.
Les warnings restent heuristiques et informatifs — aucune correction automatique.

---

## 2026-05-23 — Suppression de l'analyse audio

### Décision

Le module d'analyse audio (`scripts/audio_compare.py`) est définitivement supprimé.
L'analyse de fichiers audio MP3/WAV/OGG est hors périmètre.

### Raison du choix

Le projet doit rester simple, maintenable et orienté guitariste + chanteur. L'analyse audio
introduit des dépendances lourdes (librosa, soundfile, numpy, scipy) et un périmètre incompatible
avec l'objectif core : générer des fiches lisibles pour l'accompagnement guitare/chant.

### Conséquences

- `scripts/audio_compare.py` supprimé.
- `librosa`, `soundfile`, `numpy`, `scipy` retirés des dépendances.
- `requirements.txt` : uniquement `python-docx` (+ `reportlab` optionnel).
- `audio/` reste présent pour les MIDI optionnels, mais n'est plus référencé par les scripts.

### Périmètre des sources acceptées

Les fichiers MIDI officiels ou fournis par l'utilisateur peuvent être utilisés comme source
structurée complémentaire (ajoutés dans `sources[]` avec `name: "MIDI officiel"`).
Ils permettent de vérifier la structure, le tempo, les mesures ou certains accords.

---

## 2026-05-23 — Centralisation des chemins (config.py)

### Décision

Un module `scripts/config.py` centralise tous les chemins du projet.

### Raison du choix

Éliminer les chemins relatifs fragiles (`Path("data")`, `Path("output")`) et le chemin
Windows hardcodé (`PDF_OUTPUT_FOLDER`). Les scripts fonctionnent depuis n'importe quel
répertoire tant que le repo existe.

### Conséquences

- `scripts/config.py` : ROOT_DIR, DATA_DIR, OUTPUT_DIR, SCRIPTS_DIR.
- `collect.py` : utilise `DATA_DIR` à la place de `Path("data")`.
- `generate_docx.py` : utilise `OUTPUT_DIR` à la place de `Path("output")` et du chemin hardcodé.

---

## 2026-05-23 — Orchestrateur main.py

### Décision

`main.py` à la racine du projet orchestre le workflow complet en une commande.

### Raison du choix

Réduire la friction pour l'usage courant sans casser les scripts individuels.

### Workflow géré automatiquement

1. JSON absent → init + requêtes de recherche
2. Aucune source → message d'aide
3. Sources présentes → reconstruct + validate_harmony (automatique)
4. Non validé → display_validation (interactif)
5. Validé → generate_docx

### Conséquences

- Les scripts individuels restent utilisables directement.
- main.py appelle les scripts via subprocess avec cwd=ROOT_DIR.
- Passes des chemins absolus (depuis DATA_DIR) pour éviter les problèmes de CWD.

---

## 2026-05-23 — Fiche de synthèse musicale (3e page obligatoire)

### Décision

Tout DOCX généré contient une troisième page dédiée à la compréhension musicale et harmonique.

### Contenu

1. Tonalité + notes de la gamme
2. Ambiance harmonique (auto-générée)
3. Structure : observations globales
4. Progressions & degrés : degrés romains + nom de la progression
5. Aide-mémoire : patterns récurrents
6. Conseils guitare / chant

---

## 2026-05-23 — Analyse et proposition de simplification harmonique

### Décision

Lors de `validate_harmony.py`, le pipeline analyse si une version simplifiée est pertinente.
Si ≥ 2 accords sont simplifiables, une proposition est faite à l'utilisateur.

### Règles

- Simplification JAMAIS automatique — toujours validée par l'utilisateur.
- Trois modes : `original`, `simplified`, `both`.

---

## 2026-05-23 — Fiche mémo structure guitare (2e page obligatoire)

### Décision

Tout DOCX contient une seconde page dédiée à la mémorisation rapide de la structure.

### Contenu

- Une ligne par section : label + progression simplifiée + répétitions
- Champs optionnels : `summary_progression`, `repeat_count`, `rhythm_hint`, `mini_tab_hint`

---

## 2026-05-22 — Fichiers MIDI comme source de comparaison supplémentaire

### Décision

Les fichiers MIDI officiels peuvent être utilisés comme source complémentaire.

### Conséquences

- Le MIDI s'ajoute dans `sources[]` avec `name: "MIDI officiel"`.
- Aucun script dédié — l'analyse MIDI est manuelle ou via un utilitaire ponctuel.

---

## 2026-05-22 — Recentrage sur la fiche chant/accords

### Décision

L'outil se concentre exclusivement sur la génération de fiches chant/accords.
La comparaison audio est hors périmètre.

---

## 2026-05-21 — Validation obligatoire avant génération finale

### Décision

Claude Code doit toujours demander à l'utilisateur de valider avant de générer le `.docx`.

---

## 2026-05-21 — Format `.docx` prioritaire

### Décision

Le format final prioritaire est `.docx`. Un PDF optionnel peut être généré via reportlab.
