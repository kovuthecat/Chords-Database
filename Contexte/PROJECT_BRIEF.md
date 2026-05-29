# PROJECT_BRIEF.md

## Objectif du projet

**Éditeur local de songbook guitare/chant** : générer des fiches PDF lisibles, imprimables
et directement utilisables en répétition, à partir d'un **fichier JSON externe** conforme au template officiel.

Le projet ne génère pas les données chanson. Il les consomme.

## Principe produit

1. L'interface s'ouvre sur la **Bibliothèque** (`/library`, page d'accueil).
2. L'utilisateur crée le JSON en dehors du projet (ex: via Claude AI avec le prompt dédié).
3. L'utilisateur clique "➕ Ajouter" et uploade le JSON.
4. Le projet valide, génère le DOCX, propose un aperçu HTML interactif.
5. L'utilisateur édite les accords, les paroles et la structure directement dans l'aperçu.
6. L'utilisateur valide et exporte 2 PDFs séparés ("Exporter les fiches").
7. La Bibliothèque permet de consulter, rechercher, télécharger et gérer tous les morceaux.
8. Chaque sauvegarde crée un backup automatique — restauration en un clic depuis les Options avancées.

**Le projet ne recherche jamais automatiquement des sources sur le web.**
**Le projet n'extrait jamais depuis PDF, MIDI, audio.**

## Usage prévu

- Usage personnel : oui
- Usage local uniquement : oui
- Déploiement : non
- Connexion internet : aucune (usage entièrement local)

## Workflow

```
python app.py → http://localhost:5000 → /library (page d'accueil)
  → ➕ Ajouter → /add (upload JSON)
    → validate_song_json.py : validation (slug regex, IDs, positions)
    → generate_docx.py : DOCX + aperçu PDF
    → /song/<slug> : fiche chanson
      → aperçu HTML interactif : accords, paroles, structure, rythme
      → Transposition : boutons ±1/±2, champ custom, estimation tonalité
      → "Exporter les fiches" : 2 PDFs dans PDF_EXPORT_DIR
      → Options avancées : remplacement accord, DOCX/JSON, régénérer, backups
  → /library : bibliothèque des morceaux
    - filtres (tonalité, capo, statut révision)
    - actions primaires (Éditer, 🎵 Paroles, PDFs)
    - Options avancées par card (Mettre à jour fiches, JSON, Supprimer)
  → data/backups/<slug>/ : historique automatique des sauvegardes
```

## Format d'entrée

Le JSON doit être conforme à `song_template_with_rhythm.json`.
Le schéma formel est dans `schema/song_schema.json`.

Champs obligatoires :
- `meta.title`, `meta.artist`
- `meta.slug` : regex `^[a-z0-9_-]+$` (minuscules, chiffres, tirets, underscores)
- `sections` (avec `id` conforme `^[a-zA-Z0-9_-]+$`, `type`)
- `structure_sequence` (IDs dans l'ordre de jeu)

## Livrables

Pour chaque chanson :
- `data/song_<slug>.json` — JSON importé
- `data/backups/<slug>/<timestamp>.json` — backups automatiques (20 max)
- `output/song_<slug>.docx` — document complet
- `output/song_<slug>.pdf` — aperçu complet
- `PDF_EXPORT_DIR/Artiste - Titre - Paroles & Accords.pdf`
- `PDF_EXPORT_DIR/Artiste - Titre - Mémo Guitare.pdf`

## Fiches produites

1. **Paroles & Accords** — structure complète, accords positionnés au-dessus des paroles
2. **Mémo Guitare** — conducteur guitare multi-lignes, rythmes, répétitions

## Contraintes

- Pas de base de données.
- Pas d'authentification.
- Pas de déploiement web.
- Interface web locale uniquement (Flask).
- Pas d'analyse audio.
- Pas de scraping.
- Pas de dépendances lourdes.
- Rester simple et maintenable.
