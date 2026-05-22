# PROJECT_MAP.md

Carte synthétique du projet.

## Vue d’ensemble

Projet simple de génération de fichiers de chords pour guitare et chant.

Flux principal :

1. L’utilisateur donne un titre de chanson.
2. Claude Code recherche les accords et la structure.
3. Claude Code prépare un brouillon de validation.
4. L’utilisateur valide accords/capo/structure.
5. Claude Code génère un `.docx` final.

## Fichiers de contexte

```text
PROJECT_BRIEF.md     Objectif et périmètre du projet
CLAUDE.md            Instructions permanentes Claude Code
TASKS.md             Tâches courantes
DECISIONS.md         Décisions importantes
STATUS.md            État du projet
PROJECT_MAP.md       Carte du projet
prompts/             Prompts réutilisables
examples/            Exemples de formats attendus
```

## Règles locales importantes

- Ne jamais générer de `.docx` final sans validation préalable.
- Toujours inclure intro et parties instrumentales.
- Toujours penser guitariste + chanteur.
- Priorité à la lisibilité.
