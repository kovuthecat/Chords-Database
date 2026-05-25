# PROCESS.md — Ajouter une chanson (Claude Code)

> Fichier de référence rapide. Remplace la lecture de STATUS/TASKS/DECISIONS pour le workflow courant.
> Dernière mise à jour : 2026-05-24

---

## Ce que l'utilisateur fournit

- **PDF** : fiche chords (La Boîte à Chansons de préférence — fiable, bien structurée)
- **URL(s)** : source(s) complémentaires pour cross-check (UG, Songsterr)
  - UG retourne souvent 403 — ne pas bloquer sur ça
  - Songsterr donne les accords sans paroles
  - Le PDF BAC reste la source primaire

---

## Étapes complètes

### 1. Lire le PDF + fetcher les URLs

Claude Code lit le PDF directement (multimodal). Tenter `WebFetch` sur chaque URL.
Résultat attendu :
- PDF BAC → structure complète + paroles + accords (source de confiance)
- URL UG → souvent 403, skip
- URL Songsterr → accords sans paroles, utile pour confirmer variantes (Em vs Em7)

### 2. Comparer avec le JSON existant (si la chanson existe déjà)

Lire `data/song_<slug>.json`. Identifier les divergences vs le PDF :
- Première ligne du couplet : bon accord ?
- Refrain ("hook") répété le bon nombre de fois ?
- Interludes avec le bon motif multi-lignes ?
- Sections parasites ?
- Album renseigné ?

### 3. Construire ou reconstruire le JSON

Fichier : `data/song_<slug>.json`
Slug format : `artist-title` en kebab-case ASCII sans accents (ex: `neil-young-heart-of-gold`)

#### Template JSON

```json
{
  "meta": {
    "title": "...",
    "artist": "...",
    "album": "...",
    "key": "C",
    "key_mode": "major",
    "capo": 0,
    "tempo": null,
    "time_signature": "4/4",
    "tuning": "standard",
    "version": "studio",
    "slug": "artist-title",
    "generated_at": "2026-05-24T..."
  },
  "chords_used": ["Am", "C", "D", "Em7", "G"],
  "sources": [
    {
      "name": "PDF : Titre - Artiste - La Boîte à chansons.pdf",
      "type": "pdf",
      "path": "C:\\Users\\kovu\\Downloads\\...",
      "key": "Em",
      "capo": 0,
      "chord_set": ["Am", "C", "D", "Em7", "G"],
      "collected_at": "2026-05-24T...",
      "notes": "Extrait manuellement par Claude Code depuis PDF BAC"
    }
  ],
  "sections": [...],
  "structure_sequence": ["intro_1", "verse_1", "..."],
  "confidence": {
    "overall": 0.9,
    "structure": 0.9,
    "chords": 0.95,
    "capo": 1.0,
    "instrumental_sections": 0.9,
    "lyric_alignment": 0.85
  },
  "warnings": [],
  "variants": [],
  "validation": {
    "status": "pending",
    "validated_at": null,
    "user_corrections": []
  },
  "_collection_status": "pending_validation",
  "_extraction_method": "manual_pdf"
}
```

#### Section avec paroles (verse, chorus, bridge, outro)

```json
{
  "id": "verse_1",
  "type": "verse",
  "label": "Couplet 1",
  "is_instrumental": false,
  "chord_grid": null,
  "repeats": 1,
  "bars": 8,
  "lines": [
    {
      "chords": [
        {"chord": "Em7", "position": 0},
        {"chord": "C",   "position": 16},
        {"chord": "D",   "position": 22},
        {"chord": "G",   "position": 28}
      ],
      "lyrics": "I've been a miner for a heart of gold"
    }
  ],
  "confidence": 0.9,
  "source_agreement": 1.0,
  "chord_agreement": 1.0,
  "n_sources": 1
}
```

`position` = index caractère dans `lyrics` où l'accord commence.
Approximatif : compter les caractères jusqu'au mot concerné. L'utilisateur valide visuellement.

#### Section instrumentale (intro, interlude, solo)

```json
{
  "id": "intro_1",
  "type": "intro",
  "label": "Intro",
  "is_instrumental": true,
  "chord_grid": "Em7 D Em7 (x2)\nC D G Em7 (x3)\nEm7 D Em7",
  "repeats": 1,
  "bars": 16,
  "lines": [],
  "confidence": 0.9,
  "source_agreement": 1.0,
  "chord_agreement": 1.0,
  "n_sources": 1
}
```

`chord_grid` multi-lignes via `\n`. La notation `(x2)`, `(x3)` est reconnue par le mémo.

#### Types de sections reconnus

`intro` `verse` `pre_chorus` `chorus` `bridge` `interlude` `solo` `outro` `instrumental`

---

### 4. Lancer la pipeline

```bash
cd "c:\Users\kovu\SynologyDrive\Thibault\Projets\Chords"

python scripts/reconstruct.py data/song_<slug>.json
python scripts/validate_harmony.py data/song_<slug>.json
python scripts/display_validation.py data/song_<slug>.json
```

`display_validation.py` est interactif : taper `ok` dans le terminal génère le DOCX directement.
Sinon, capturer la sortie et la montrer à l'utilisateur pour validation manuelle.

### 5. Présenter le brouillon

Montrer à l'utilisateur :
- Tonalité + capo
- Structure complète (toutes les sections dans l'ordre)
- Accords utilisés
- Score de confiance
- Avertissements (certains sont normaux, cf. ci-dessous)

Demander explicitement la validation avant de continuer.

### 6. Appliquer les corrections (si demandées)

Exemples courants :
- Changer un accord dans le JSON → modifier le champ `chord` dans la section concernée
- Ajouter une variante (Em → Em7) → replace_all dans le JSON
- Corriger un chord_grid d'intro/interlude → éditer la chaîne `chord_grid`
- Relancer validate_harmony après corrections

### 7. Marquer comme validé + générer

Après confirmation utilisateur :

```python
# Dans le JSON : changer
"status": "user_validated",
"validated_at": "2026-05-24T...",
```

Puis :

```bash
python scripts/generate_docx.py data/song_<slug>.json --split-pdf
```

Produit :
- `output/song_<slug>.docx`
- `C:\Users\kovu\SynologyDrive\Thibault\Guitartabs\Chords\song_<slug>_paroles_chords.pdf`
- `C:\Users\kovu\SynologyDrive\Thibault\Guitartabs\Chords\song_<slug>_memo_guitare.pdf`
- `C:\Users\kovu\SynologyDrive\Thibault\Guitartabs\Chords\song_<slug>_comprendre_morceau.pdf`

---

## Avertissements courants normaux

| Avertissement | Normal ? |
|---|---|
| "Refrain (chorus) absent" | ✓ si le morceau n'a pas de chorus distinct |
| "Source unique" | ✓ si seul le PDF est disponible |
| "Section X absente de 1/2 source(s)" | ✓ si une URL était inaccessible |

---

## Pièges courants

- **Première ligne du couplet** : vérifier si elle commence sur Em ou sur C/G/autre (pas toujours Em)
- **Refrain répété** : compter le nombre de fois que "That keep me searchin'" ou équivalent apparaît
- **Em vs Em7** : BAC écrit souvent Em, Songsterr confirme Em7 — demander à l'utilisateur
- **Interludes** : vérifier le nombre de fois que le motif se répète (x3 ≠ x4)
- **Outro** : section non-instrumentale même sans paroles traditionnelles

---

## Chansons existantes

| Chanson | Artiste | Slug | Méthode |
|---|---|---|---|
| Jimmy | Moriarty | `moriarty-jimmy` | manuel |
| Wish You Were Here | Pink Floyd | `pink-floyd-wish-you-were-here` | manuel |
| Heart of Gold | Neil Young | `neil-young-heart-of-gold` | manuel (rebuild PDF BAC 2026-05-24) |
| La Symphonie des Éclairs | Zaho de Sagazan | `zaho-de-sagazan-la-symphonie-des-eclairs` | manuel |
| Endlessly | Muse | `muse-endlessly` | manuel |
| On My Way | Cocoon | `cocoon-on-my-way` | manuel |
| Hotel California | Eagles | `eagles-hotel-california` | manuel (rebuild PDF BAC 2026-05-24) |
