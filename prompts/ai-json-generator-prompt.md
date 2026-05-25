# Prompt IA — Générer un fichier song JSON pour la pipeline Chords

## Contexte

Ce prompt est destiné à une IA externe (ChatGPT, Gemini, Perplexity, etc.) pour produire un fichier JSON conforme au schéma attendu par la pipeline Python du projet Chords.

La pipeline comprend les étapes suivantes :
1. **collect** — ingestion de sources (remplacée ici par ta génération)
2. **reconstruct** — fusion multi-sources (optionnel si une seule source)
3. **validate_harmony** — vérification harmonique
4. **display_validation** — validation manuelle utilisateur
5. **generate_docx** — génération du fichier Word final

Le JSON que tu génères sera injecté directement à l'étape 3 (validate_harmony), en bypassant collect et reconstruct.

---

## Ta mission

Génère un fichier JSON complet et valide pour la chanson suivante :

**Titre :** [TITRE]
**Artiste :** [ARTISTE]

Consulte des sources publiques fiables (Ultimate Guitar, La Boîte à Musique, Songsterr, Chordify, etc.) et produis un fichier JSON conforme au schéma décrit ci-dessous.

---

## Schéma JSON — description complète

```jsonc
{
  // ── MÉTADONNÉES ───────────────────────────────────────────────────────────
  "meta": {
    "title": "Titre exact de la chanson",           // string
    "artist": "Nom de l'artiste",                    // string
    "key": "F",                                      // string | null — note anglaise : A B C D E F G + b/#
    "key_mode": "major",                             // "major" | "minor" | null
    "capo": 0,                                       // int — 0 = pas de capo, sinon numéro de case
    "tempo": 76,                                     // int | null — BPM approximatif
    "time_signature": "4/4",                         // string — "4/4", "3/4", "6/8", etc.
    "tuning": "standard",                            // "standard" | "drop D" | "open G" | etc.
    "version": "studio",                             // "studio" | "live" | "acoustique" | etc.
    "slug": "artiste-titre",                         // string — kebab-case sans accents : prénom-nom-titre
    "generated_at": "2026-05-25T12:00:00",           // string ISO 8601
    "album": "Nom de l'album (année)"               // string | omis si inconnu
  },

  // ── ACCORDS UTILISÉS ──────────────────────────────────────────────────────
  // Liste TRIÉE de tous les accords distincts présents dans le JSON
  "chords_used": ["Am", "C", "F", "G"],

  // ── SOURCES CONSULTÉES ────────────────────────────────────────────────────
  "sources": [
    {
      "name": "Ultimate Guitar",                     // string — nom de la source
      "url": "https://...",                          // string — URL exacte ou "" si indisponible
      "key": "F",                                    // string | null — tonalité indiquée par la source
      "capo": 0,                                     // int
      "chord_set": ["Am", "C", "F", "G"],           // string[] — accords listés par cette source
      "collected_at": "2026-05-25T12:00:00",         // string ISO 8601
      "notes": "Version 5 étoiles, 1 200 votes"     // string — info utile sur la source
    }
    // Ajoute autant de sources que tu as consultées
  ],

  // ── SECTIONS ──────────────────────────────────────────────────────────────
  "sections": [
    // Chaque section est un objet. Deux types mutuellement exclusifs :
    // A) Section INSTRUMENTALE (intro, interlude, solo) → chord_grid rempli, lines = []
    // B) Section CHANTÉE → chord_grid = null, lines rempli

    // EXEMPLE A — section instrumentale
    {
      "id": "intro_1",                              // string — format "{type}_{numéro}"
      "type": "intro",                              // voir types autorisés ci-dessous
      "label": "Intro",                             // string — libellé français affiché
      "is_instrumental": true,                      // bool
      "chord_grid": "| Am | F | C | G |",          // string — grille de mesures avec |
      "repeats": 2,                                 // int — nombre de répétitions de la section
      "bars": 4,                                    // int | null — nombre de mesures
      "lines": [],                                  // toujours [] pour les sections instrumentales
      "confidence": 0.85,                           // float 0.0–1.0
      "source_agreement": 1.0,                      // float 0.0–1.0 (1.0 si source unique)
      "chord_agreement": 1.0,                       // float 0.0–1.0 (1.0 si source unique)
      "n_sources": 1                                // int — nombre de sources ayant cette section
    },

    // EXEMPLE B — section chantée
    {
      "id": "verse_1",
      "type": "verse",
      "label": "Couplet 1",
      "is_instrumental": false,
      "chord_grid": null,
      "repeats": 1,
      "bars": null,
      "lines": [
        // Chaque ligne = une ligne de paroles avec ses accords
        {
          "chords": [
            {
              "chord": "Am",     // string — accord en notation anglaise
              "position": 0      // int — index du caractère dans `lyrics` où sonne l'accord
            },
            {
              "chord": "F",
              "position": 18     // → l'accord F sonne au 18ème caractère de la ligne
            }
          ],
          "lyrics": "Je vous parle d'un temps"   // string — paroles de la ligne
        }
        // ... une entrée par ligne de paroles
      ],
      "confidence": 0.85,
      "source_agreement": 1.0,
      "chord_agreement": 1.0,
      "n_sources": 1
    }
  ],

  // ── SÉQUENCE STRUCTURELLE ─────────────────────────────────────────────────
  // Ordre de jeu de la chanson — les IDs peuvent se répéter (ex: même refrain joué 3 fois)
  "structure_sequence": [
    "intro_1",
    "verse_1",
    "chorus_1",
    "verse_2",
    "chorus_1",    // même refrain, même ID → la section chorus_1 est répétée ici
    "bridge_1",
    "chorus_1",
    "outro_1"
  ],

  // ── SCORES DE CONFIANCE GLOBAUX ───────────────────────────────────────────
  "confidence": {
    "overall": 0.85,               // float — moyenne pondérée globale
    "structure": 0.90,             // float — confiance sur la structure des sections
    "chords": 0.85,                // float — confiance sur les accords
    "capo": 0.95,                  // float — confiance sur le capo
    "instrumental_sections": 0.80, // float — confiance sur les parties instrumentales
    "lyric_alignment": 0.75        // float — confiance sur le placement des accords
  },

  // ── AVERTISSEMENTS ────────────────────────────────────────────────────────
  "warnings": [
    {
      "severity": "low",           // "low" | "medium" | "high"
      "section": "interlude_1",    // string | null — ID de section concernée
      "message": "Description du problème ou de l'incertitude"
    }
  ],

  // ── VARIANTES ─────────────────────────────────────────────────────────────
  "variants": [
    {
      "name": "Version live",
      "differences": "Tempo plus lent, refrain répété 4 fois"
    }
  ],

  // ── VALIDATION ────────────────────────────────────────────────────────────
  "validation": {
    "status": "pending",           // TOUJOURS "pending" à la génération
    "validated_at": null,
    "user_corrections": []
  },

  "_collection_status": "ai_generated"   // NE PAS MODIFIER — identifie l'origine
}
```

---

## Types de sections autorisés

| `type`       | `label` français suggéré | `is_instrumental` par défaut |
|--------------|--------------------------|------------------------------|
| `intro`      | Intro                    | `true`                       |
| `verse`      | Couplet N                | `false`                      |
| `pre_chorus` | Pré-refrain              | `false`                      |
| `chorus`     | Refrain                  | `false`                      |
| `bridge`     | Pont                     | `false`                      |
| `solo`       | Solo                     | `true`                       |
| `interlude`  | Interlude                | `true`                       |
| `outro`      | Outro                    | `false` ou `true`            |
| `breakdown`  | Breakdown                | `false`                      |

---

## Règles de notation des accords

- Notation **anglaise** obligatoire : A, B, C, D, E, F, G
- Altérations : `b` (bémol) ou `#` (dièse) — ex : `Bb`, `F#`
- Qualité : `m` (mineur), `maj` (majeur avec extension), `aug`, `dim`, `sus`
- Extensions : `7`, `9`, `11`, `13`, `add9`, etc. — ex : `Am7`, `Cmaj7`, `D9`
- Basse : `/note` — ex : `C/G`, `Am/E`
- Exemples valides : `Am`, `F#m`, `Bb`, `D7`, `Cmaj7`, `G/B`, `Esus4`, `Bm7b5`

---

## Règle de `position` dans une ligne chantée

`position` est l'**index du caractère** (0-basé) dans la chaîne `lyrics` où l'accord doit sonner.

```
lyrics   : "Je vous parle d'un temps"
positions:  0         1         2
            0123456789012345678901234
```

Si l'accord `F` sonne sur le mot "d'un" (position 18) :
```json
{"chord": "F", "position": 18}
```

Si tu n'as pas d'information précise sur le placement, utilise des positions approximatives proportionnelles à la longueur de la ligne (répartis les accords de façon égale). Le minimum est `position: 0` pour le premier accord.

---

## Format d'ID des sections

- Format : `{type}_{numéro}` — ex : `verse_1`, `verse_2`, `chorus_1`
- Le numéro est un entier incrémental par type dans l'ordre d'apparition dans `sections`
- Si le même refrain est joué plusieurs fois, utilise **un seul objet** dans `sections` et répète son ID dans `structure_sequence`
- Si deux refrains ont des paroles légèrement différentes, crée `chorus_1` et `chorus_2`

---

## Contraintes de génération

1. Le JSON doit être **valide** (parseable par `json.loads()`).
2. Tous les accords dans `lines` et `chord_grid` doivent être présents dans `chords_used`.
3. Tous les IDs dans `structure_sequence` doivent exister dans `sections`.
4. `_collection_status` doit valoir exactement `"ai_generated"`.
5. `validation.status` doit valoir exactement `"pending"`.
6. `source_agreement` et `chord_agreement` valent `1.0` si tu n'as qu'une seule source.
7. Ne pas inventer des paroles. Si tu n'es pas certain d'une ligne, mets la valeur la plus proche connue et ajoute un warning `severity: "low"`.
8. Ne pas mettre de commentaires dans le JSON final (les commentaires ci-dessus sont pédagogiques).
9. Encoder en **UTF-8**, conserver les caractères accentués (é, è, à, etc.).

---

## Format de sortie attendu

Réponds **uniquement** avec le JSON brut. Pas d'explication, pas de markdown, pas de balise de code. Le contenu doit commencer directement par `{` et se terminer par `}`.

---

## Exemple de fichier valide

Voir ci-dessous un exemple complet pour *La Bohème* de Charles Aznavour :

```json
{
  "meta": {
    "title": "La Bohème",
    "artist": "Charles Aznavour",
    "key": "F",
    "key_mode": "major",
    "capo": 0,
    "tempo": 76,
    "time_signature": "4/4",
    "tuning": "standard",
    "version": "studio",
    "slug": "charles-aznavour-la-boheme",
    "generated_at": "2026-05-25T12:00:00"
  },
  "chords_used": ["Am", "Bb", "C", "C7", "Dm", "F", "Gm"],
  "sources": [
    {
      "name": "Ultimate Guitar",
      "url": "https://ultimate-guitar.com/...",
      "key": "F",
      "capo": 0,
      "chord_set": ["F", "Am", "Dm", "Gm", "Bb", "C", "C7"],
      "collected_at": "2026-05-25T12:00:00",
      "notes": "Version 5 étoiles, 847 votes"
    }
  ],
  "sections": [
    {
      "id": "intro_1",
      "type": "intro",
      "label": "Intro",
      "is_instrumental": true,
      "chord_grid": "| F | Dm | Bb | C |",
      "repeats": 2,
      "bars": 4,
      "lines": [],
      "confidence": 0.90,
      "source_agreement": 1.0,
      "chord_agreement": 1.0,
      "n_sources": 1
    },
    {
      "id": "verse_1",
      "type": "verse",
      "label": "Couplet 1",
      "is_instrumental": false,
      "chord_grid": null,
      "repeats": 1,
      "bars": null,
      "lines": [
        {
          "chords": [{"chord": "F", "position": 0}, {"chord": "Am", "position": 16}],
          "lyrics": "Je vous parle d'un temps"
        },
        {
          "chords": [{"chord": "Dm", "position": 0}, {"chord": "Gm", "position": 14}],
          "lyrics": "Que les moins de vingt ans"
        },
        {
          "chords": [{"chord": "C", "position": 0}],
          "lyrics": "Ne peuvent pas connaître"
        }
      ],
      "confidence": 0.85,
      "source_agreement": 1.0,
      "chord_agreement": 1.0,
      "n_sources": 1
    },
    {
      "id": "chorus_1",
      "type": "chorus",
      "label": "Refrain",
      "is_instrumental": false,
      "chord_grid": null,
      "repeats": 1,
      "bars": null,
      "lines": [
        {
          "chords": [{"chord": "Bb", "position": 0}, {"chord": "F", "position": 10}],
          "lyrics": "La Bohème, la Bohème"
        },
        {
          "chords": [{"chord": "C7", "position": 0}, {"chord": "F", "position": 12}],
          "lyrics": "Ça voulait dire on est heureux"
        }
      ],
      "confidence": 0.88,
      "source_agreement": 1.0,
      "chord_agreement": 1.0,
      "n_sources": 1
    },
    {
      "id": "outro_1",
      "type": "outro",
      "label": "Outro",
      "is_instrumental": false,
      "chord_grid": null,
      "repeats": 1,
      "bars": null,
      "lines": [
        {
          "chords": [{"chord": "Bb", "position": 0}, {"chord": "F", "position": 10}],
          "lyrics": "La Bohème, la Bohème"
        }
      ],
      "confidence": 0.80,
      "source_agreement": 1.0,
      "chord_agreement": 1.0,
      "n_sources": 1
    }
  ],
  "structure_sequence": [
    "intro_1",
    "verse_1",
    "chorus_1",
    "verse_1",
    "chorus_1",
    "outro_1"
  ],
  "confidence": {
    "overall": 0.86,
    "structure": 0.90,
    "chords": 0.87,
    "capo": 1.0,
    "instrumental_sections": 0.90,
    "lyric_alignment": 0.75
  },
  "warnings": [],
  "variants": [
    {
      "name": "Version live Palais des Congrès",
      "differences": "Tempo plus lent (~68 bpm), refrain répété 4 fois"
    }
  ],
  "validation": {
    "status": "pending",
    "validated_at": null,
    "user_corrections": []
  },
  "_collection_status": "ai_generated"
}
```

---

## Intégration dans la pipeline

Une fois le JSON généré, sauvegarde-le sous :
```
Chords/data/song_{slug}.json
```

Puis lance les étapes suivantes :
```bash
# Vérification harmonique
python scripts/validate_harmony.py data/song_{slug}.json

# Affichage pour validation manuelle
python scripts/display_validation.py data/song_{slug}.json

# Génération du DOCX (après validation)
python scripts/generate_docx.py data/song_{slug}.json
```
