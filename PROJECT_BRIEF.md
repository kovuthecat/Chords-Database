# PROJECT_BRIEF.md

## Objectif du projet

**Éditeur local de songbook guitare/chant** : générer des fiches PDF lisibles, imprimables
et directement utilisables en répétition, à partir d'un **fichier JSON externe** conforme au template officiel.

Le projet ne génère pas les données chanson. Il les consomme.

## Principe produit

1. Le JSON est créé en dehors du projet (ex: via Claude AI avec le prompt dédié).
2. L'utilisateur uploade le JSON dans l'interface web locale.
3. Le projet valide, génère le DOCX, propose un aperçu HTML interactif.
4. L'utilisateur édite les accords, les paroles et la structure directement dans l'aperçu.
5. L'utilisateur valide et exporte 2 PDFs séparés.
6. La Bibliothèque (`/library`) permet de consulter, rechercher, télécharger et gérer tous les morceaux.
7. Chaque sauvegarde crée un backup automatique — restauration en un clic depuis l'historique.

**Le projet ne recherche jamais automatiquement des sources sur le web.**
**Le projet n'extrait jamais depuis PDF, MIDI, audio.**

## Usage prévu

- Usage personnel : oui
- Usage local uniquement : oui
- Déploiement : non
- Connexion internet : aucune (usage entièrement local)

## Workflow

```
JSON externe conforme au template
  → python app.py (http://localhost:5000)
    → validate_song_json.py : validation de la structure (slug regex, IDs, positions)
    → generate_docx.py : DOCX complet + aperçu PDF
    → [édition inline dans l'aperçu HTML interactif]
      - accords paroles : modifier / supprimer / insérer
      - accords instrumentaux : modifier / supprimer / insérer
      - paroles : édition texte inline
      - structure + rythme : éditeurs dédiés
    → generate_split_pdf() : 2 PDFs exportés dans PDF_EXPORT_DIR
  → /library : bibliothèque des morceaux validés
    - recherche live (titre, artiste, album)
    - télécharger JSON
    - régénérer PDFs
    - supprimer
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
