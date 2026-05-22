# TASKS.md

## Règles

- Une chanson = une tâche.
- Toujours produire un brouillon de validation avant le `.docx` final.
- Ne jamais générer le document final sans validation des accords, du capo et de la structure.
- La Boîte à Chansons est la source de référence prioritaire.
- Garder le workflow simple.

## Workflow standard par chanson

```
1. collect.py "Titre" "Artiste"
2. collect.py data/song_slug.json --ingest "Source" --file fichier.txt
   (répéter pour 2-3 sources)
3. reconstruct.py data/song_slug.json
4. validate_harmony.py data/song_slug.json
5. display_validation.py data/song_slug.json   ← validation utilisateur
6. generate_docx.py data/song_slug.json
```

## À faire

- [ ] `main.py` — orchestration complète en une commande (titre + artiste → DOCX).
- [ ] Afficher l'album dans le bloc en-tête du DOCX.
- [ ] Export PDF optionnel (`docx2pdf` ou LibreOffice CLI).

## En cours

- [ ] Affiner le placement accords/paroles (review manuelle des DOCX générés).

## Fait

- [x] Concevoir la méthodologie complète (pipeline, scoring, JSON, risques).
- [x] T1 — Structure répertoires + `schema/song_schema.json`.
- [x] T2 — `scripts/collect.py` (init, parser chord, ingestion multi-sources, statut).
- [x] T3 — `scripts/reconstruct.py` (unification, source_agreement, divergences).
- [x] T4 — `scripts/validate_harmony.py` (tonalité, diatonique, capo, scoring).
- [x] T5 — `scripts/display_validation.py` (brouillon terminal, boucle OK/corrections).
- [x] T7 — `scripts/generate_docx.py` (Consolas, keep_with_next, grilles multi-lignes, plein rendu reprises).
- [x] Pipeline end-to-end testé et affiné sur 6 chansons.

## Chansons traitées

| Chanson | Artiste | Sources | Score | Fichier |
|---|---|---|---|---|
| Jimmy | Moriarty | UG + BAC | 96% | `song_moriarty-jimmy.docx` |
| Wish You Were Here | Pink Floyd | BAC + UG + Songsterr | 96% | `song_pink-floyd-wish-you-were-here.docx` |
| Heart of Gold | Neil Young | BAC + UG | 100% | `song_neil-young-heart-of-gold.docx` |
| La Symphonie des Éclairs | Zaho de Sagazan | PDF source | 100% | `song_zaho-de-sagazan-la-symphonie-des-eclairs.docx` |
| Endlessly | Muse | PDF source | 100% | `song_muse-endlessly.docx` |

## Bugs corrigés (bénéficient aux futures chansons)

- [x] Regex `tonali...` sans `m` → Am non reconnu comme mineur.
- [x] `key_mode` non extrait de clé brute ("Am" → key=A, mode=minor).
- [x] Grilles multi-lignes : overwrite → concaténation `\n`.
- [x] Outro auto-instrumental → désactivé (seuls intro/interlude/solo).
- [x] Faux positif capo rel. maj/min → tolérance ±3 demi-tons.
- [x] Regex chord : `Am7/4`, `Bm7b5`, `Asus4`, `F/A`, `b5` maintenant reconnus.

## Améliorations futures

- [ ] Export PDF.
- [ ] Transposition automatique.
- [ ] Diagrammes d'accords (ASCII ou images).
- [ ] Plusieurs versions : originale / capo simplifié / tonalité adaptée voix.
- [ ] Gestion des tablatures simples pour intro/solo.
