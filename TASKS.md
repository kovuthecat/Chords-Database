# TASKS.md

## Workflow par chanson

1. Créer un JSON conforme au template (`song_template_with_rhythm.json`) via Claude AI ou manuellement.
2. Lancer l'interface web : `python app.py` → http://localhost:5000
3. Uploader le JSON.
4. Vérifier et éditer l'aperçu HTML interactif :
   - **Sections avec paroles** :
     - Clic sur accord → popup modifier/supprimer (confirmation avant suppression)
     - Survol ligne → points `+` pour insérer un accord
     - Clic sur paroles → édition inline du texte (sauvegarde AJAX)
   - **Sections instrumentales** :
     - Clic sur accord (pp / chord_grid / summary) → modifier/supprimer
     - Survol → points `+` pour insérer un accord entre les existants
   - **Éditeur structure** : réordonner, renommer, changer type/répétitions
   - **Éditeur rythme** : pattern + feel par section
   - **Bouton "Sauvegarder et rafraîchir l'aperçu"** : sauvegarde structure + rythme en un clic
5. Cliquer "Valider et exporter 2 PDFs" (Paroles & Accords + Mémo Guitare).
6. Retrouver les morceaux validés dans la Bibliothèque : http://localhost:5000/library

**En CLI :**
```bash
python main.py data/song_<slug>.json --split-pdf
```

## Tâches techniques courantes

### Ajouter une chanson

1. Préparer le JSON en suivant `song_template_with_rhythm.json`.
2. Uploader via l'interface web.
3. Si des erreurs de validation → corriger le JSON et reuploader.

**Règles slug** : `meta.slug` doit suivre `^[a-z0-9_-]+$` (minuscules, chiffres, tirets, underscores uniquement).

### Corriger une chanson existante

1. Ouvrir la fiche chanson → cliquer sur un accord pour le modifier/supprimer.
   - Fonctionne sur les sections avec paroles ET sur les sections instrumentales (pp, chord_grid, summary).
2. Survol d'une ligne de paroles → `+` pour insérer un accord (paroles) ou accord instrumental.
3. Clic sur une ligne de paroles pour l'éditer directement.
4. Modifier structure/rythme dans les éditeurs, puis "Sauvegarder et rafraîchir l'aperçu".
5. Pour des corrections structurelles complexes : éditer `data/song_<slug>.json`, puis "Régénérer depuis un JSON corrigé".

### Restaurer une version précédente

1. Ouvrir la fiche chanson.
2. Ouvrir "Historique / Backups" (dans la section Actions).
3. Cliquer "Restaurer" sur la version souhaitée.
4. Confirmer — la version actuelle est sauvegardée en backup avant écrasement.

### Configurer PDF_EXPORT_DIR

Créer ou modifier `.env.local` à la racine du projet :
```
PDF_EXPORT_DIR=C:\Users\kovu\SynologyDrive\Thibault\Guitartabs\Chords
```

### Supprimer une chanson

- Dans la Bibliothèque (`/library`) → bouton "Supprimer" (confirmation requise).
- Supprime : `data/song_<slug>.json`, `output/song_<slug>.*`, PDFs exportés dans `PDF_EXPORT_DIR`.
- Note : les backups dans `data/backups/<slug>/` ne sont PAS supprimés (conservation intentionnelle).

### Télécharger le JSON d'une chanson

- Dans la Bibliothèque (`/library`) → bouton "JSON" sur la card.
- Ou directement : `GET /song/<slug>/download-json`

### Ajouter/modifier la logique métier

- Fiche mémo → `scripts/memo.py`
- Génération DOCX/PDF → `scripts/generate_docx.py`
- Édition JSON ciblée → `scripts/editor.py` (13 fonctions)
- Backup/restauration → `scripts/backup.py`
- Validation JSON → `scripts/validate_song_json.py`
- Chemins + .env.local → `scripts/config.py`
- Bibliothèque → route `/library` dans `app.py` + `templates/library.html`
- Aperçu interactif → `templates/_preview.html`

### Lancer les tests

```bash
python -m pytest tests/ -v
```

129 tests — 0 échec.

## À faire (prochaine session — 2026-05-26)

- [ ] Améliorer la lisibilité de la fiche Mémo Guitare (PDF/DOCX)
- [ ] Améliorer l'interface webapp (UX/UI)

---

## Chansons dans le repo

| Fichier | Statut |
|---|---|
| `song_moriarty-jimmy.json` | user_validated |
| `song_pink-floyd-wish-you-were-here.json` | user_validated |
| `song_neil-young-heart-of-gold.json` | user_validated |
| `song_zaho-de-sagazan-la-symphonie-des-eclairs.json` | user_validated |
| `song_muse-endlessly.json` | user_validated |
| `song_cocoon-on-my-way.json` | user_validated |
