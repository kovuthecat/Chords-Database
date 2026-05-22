# ROADMAP.md

## MVP — Terminé ✓

- [x] Pipeline complet : titre → collecte → reconstruction → validation → DOCX.
- [x] Parser texte chord : sections FR/EN, grilles multi-lignes, accords altérés.
- [x] Reconstruction multi-sources avec scoring de confiance et détection de divergences.
- [x] Validation harmonique : tonalité, accords hors gamme, cohérence capo.
- [x] Brouillon de validation terminal obligatoire avant génération.
- [x] DOCX lisible : Consolas, accords visibles, keep_with_next, reprises complètes.
- [x] 5 chansons traitées : Jimmy, WYWH, Heart of Gold, La Symphonie des Éclairs, Endlessly.

## Version 1 — Prochaine priorité

- [ ] `main.py` : une seule commande `python main.py "Titre" "Artiste"` pour tout le pipeline.
- [ ] Album visible dans le DOCX (bloc en-tête).
- [ ] Tempo affiché dans le DOCX quand disponible.
- [ ] Meilleure gestion des PDF source : ingestion directe sans fichier texte intermédiaire.

## Version 2

- [ ] Export PDF (`docx2pdf` ou LibreOffice headless CLI).
- [ ] Transposition automatique (ex: capo 2 → afficher les accords transposés).
- [ ] Plusieurs versions dans un même document (ex: version capo / version ouverte).
- [ ] Diagrammes d'accords en ASCII dans le DOCX.

## Version 1.5 — Module audio (en cours)

Étude de faisabilité réalisée. Architecture : `scripts/audio_compare.py` + `audio/` (gitignored) + `output/audio_report_*.md`.

- [x] A1 — `audio/` + `.gitkeep`
- [x] A2 — Squelette `audio_compare.py` (argparse, chargement, rapport vide)
- [ ] A3 — Tempo + tonalité (fiable)
- [ ] A4 — Segmentation structure (orientatif)
- [ ] A5 — Chromagramme + progression accords (expérimental)
- [ ] A6 — Divergences + recommandations
- [ ] A8 — Tests + calibrage

Dépendance : `librosa` + `soundfile` uniquement.

## Idées futures (hors périmètre actuel)

- Tablatures simplifiées pour intros/solos connus.
- Interface web légère (pas de priorité — le workflow CLI est suffisant).
- Base locale de chansons (SQLite ou JSON index) pour éviter de recollectes.

## À éviter

- Interface graphique complète.
- Scraping automatisé fragile (préférer WebSearch + ingestion manuelle).
- Génération sans validation utilisateur (règle absolue du projet).
- Dépendances lourdes (rester sur : requests, python-docx, beautifulsoup4).
