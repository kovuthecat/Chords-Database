# DECISIONS.md

Journal des décisions produit et techniques.

## 2026-05-21 — Validation obligatoire avant génération finale

### Décision

Claude Code doit toujours demander à l’utilisateur de valider les accords, le capo éventuel et la structure avant de générer le fichier `.docx` final.

### Contexte

Les sources d’accords peuvent diverger selon les sites. Pour un usage guitare/chant, un mauvais capo ou une mauvaise tonalité rend le document peu utile.

### Raison du choix

La validation manuelle évite de générer des documents faux ou difficiles à chanter.

### Conséquences

- Le workflow se fait en deux temps : brouillon puis document final.
- Le fichier final n’est généré qu’après accord explicite de l’utilisateur.

## 2026-05-21 — Format `.docx` prioritaire

### Décision

Le format final prioritaire est `.docx`.

### Raison du choix

Le `.docx` est facile à relire, modifier, imprimer et partager.

### Conséquences

Un fichier Markdown intermédiaire peut être utilisé pour simplifier le travail, mais le livrable attendu reste un document `.docx`.
