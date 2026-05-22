# Générateur de fiches chords guitare/chant

Ce dossier contient les fichiers de contexte à fournir à Claude Code pour produire des fichiers `.docx` de chords à partir du titre d’une chanson.

## Principe

Claude Code doit :

1. rechercher les accords et la structure ;
2. préparer un brouillon de validation ;
3. demander validation des accords, du capo et de la structure ;
4. générer le `.docx` final seulement après validation.

## Fichiers principaux

- `PROJECT_BRIEF.md` : périmètre du projet
- `CLAUDE.md` : instructions permanentes Claude Code
- `prompts/chord-sheet-workflow.md` : prompt opérationnel pour une chanson
- `examples/chord-sheet-template.md` : exemple de structure attendue

## Utilisation recommandée

1. Ouvrir ce dossier dans Claude Code.
2. Demander : “Lis `CLAUDE.md` et `PROJECT_BRIEF.md`.”
3. Utiliser `prompts/chord-sheet-workflow.md` pour lancer une chanson.
4. Valider le brouillon.
5. Demander la génération finale `.docx`.
