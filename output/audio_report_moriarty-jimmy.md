# Rapport de comparaison audio — Jimmy (Moriarty)
Généré : 2026-05-22T11:35:35  
Fichier audio : `Moriarty - Jimmy (320).mp3` (2:50)  
JSON source : `data\song_moriarty-jimmy.json`

---

## Résumé

**Score global : 0.85 — OK**

| Dimension | Résultat |
|-----------|---------|
| Tempo | 127.8 BPM (JSON vide) |
| Tonalité | Relatif conforme — Bb minor et C# major partagent la même gamme (ambig… |
| Structure | 9 sections vs 11 JSON — écart 2 |
| Accords | 5/6 accords JSON retrouvés (expérimental) |

> Rapport orientatif. **La validation humaine reste obligatoire avant génération DOCX.**

---

## Métadonnées

| Dimension | Audio estimé | JSON actuel | Statut |
|-----------|-------------|-------------|--------|
| Tempo | 127.8 BPM | null | Info (JSON vide) |
| Tonalité | C# major | A minor (capo 1 → sonne Bb minor) | Relatif conforme — Bb minor et C# major partagent la même gamme (ambiguïté KS normale) |
| Durée | 2:50 | — | Info |

---

## Analyse de structure

- Transitions détectées : **9** sections
- Sections JSON (`structure_sequence`) : **11**
- Évaluation : Écart de 2 — vérifier les répétitions
- Zones répétées (matrice de récurrence) : 1
- Frontières estimées : 0:10 | 0:25 | 0:52 | 1:27 | 1:42 | 1:56 | 2:10 | 2:44

Confiance structure : **0.62** (orientatif)

---

## Analyse harmonique

> Confiance faible — templates triades sur audio polyphonique.

**Top 6 accords estimés :** C# (18%)  F# (17%)  G# (15%)  D# (12%)  A#m (10%)  Fm (9%)

**Accords JSON (normalisés) :** `A#m C# F F# Fm G#`

### Correspondance JSON ↔ audio

| Accord JSON | Trouvé en audio | Fréquence estimée |
|------------|----------------|-------------------|
| A#m | Oui | 10% |
| C# | Oui | 18% |
| F | **Non détecté** | 3% |
| F# | Oui | 17% |
| Fm | Oui | 9% |
| G# | Oui | 15% |

### Accords audio non présents dans le JSON

| Accord | Fréquence | Note |
|--------|-----------|------|
| A# | — | Absent du JSON — vérifier |
| C#m | — | Absent du JSON — vérifier |
| D# | 12% | Absent du JSON — vérifier |

### Accords suspects

| Accord JSON | Signal audio | Remarque |
|------------|-------------|----------|
| F | Absent du top-8 audio | Non détecté — vérifier manuellement |

---

## Divergences

| Dimension | Sévérité | JSON | Audio | Note |
|-----------|---------|------|-------|------|
| Tempo | Info | null | 127.8 BPM | JSON vide — envisager mise à jour |
| Tonalité | Info | Bb minor | C# major | Relatif conforme — même gamme, ambiguïté KS normale |
| Structure | Info | 11 sections | 9 sections | Écart de 2 — vérifier répétitions/frontières |
| Accord | Faible | F | Non dans top-8 | Peu fréquent ou confusion maj/min |
| Accord | Faible | — | A# | Absent du JSON — artefact probable |
| Accord | Faible | — | C#m | Absent du JSON — artefact probable |
| Accord | Faible | — | D# | Absent du JSON — artefact probable |

---

## Scores de confiance

| Dimension | Score | Fiabilité |
|-----------|-------|-----------|
| Tempo      | 0.95  | Élevée |
| Tonalité   | 0.24    | Élevée |
| Structure  | 0.62 | Orientatif |
| Progression| 0.45 | Faible (expérimental) |
| Accords    | 0.3 | Faible (expérimental) |

---

## Recommandations

- [ ] Tempo estimé 127.8 BPM — envisager `"tempo": 128` dans le JSON (confiance : 0.95)
- [ ] Structure : audio détecte 9 sections, JSON en annonce 11 (écart 2) — vérifier les répétitions
- [ ] Accord `F` (JSON) absent du top-8 audio — vérifier manuellement
- [ ] Accord `A#` détecté en audio mais absent du JSON — vérifier
- [ ] Accord `C#m` détecté en audio mais absent du JSON — vérifier
- [ ] Accord `D#` détecté en audio mais absent du JSON — vérifier

---

> Ce rapport est **orientatif**. Les estimations d'accords sont produites sur audio
> polyphonique (guitare + voix + basse) avec des templates triades uniquement.
> **La validation humaine reste obligatoire avant génération DOCX.**