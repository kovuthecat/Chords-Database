# CLAUDE.md

Instructions permanentes pour Claude Code dans ce projet.

## Rôle

Tu aides à produire des fichiers de chords au format document pour guitare et chant.

Le livrable final doit être un fichier `.docx` clair, imprimable et utilisable par :

- un guitariste ;
- un chanteur ;
- ou une personne qui chante en s’accompagnant à la guitare.

## Workflow obligatoire

Pour chaque chanson :

1. Identifier le titre exact et l’artiste.
2. Rechercher les accords et la structure sur des sources pertinentes, par exemple :
   - Songsterr ;
   - La Boîte à Musique ;
   - Ultimate Guitar ;
   - Chordify ;
   - autres sources fiables.
3. Comparer les sources quand c’est possible.
4. Préparer un brouillon de validation contenant :
   - titre ;
   - artiste ;
   - tonalité ;
   - capo proposé ou absence de capo ;
   - liste des accords ;
   - structure complète : intro, couplets, refrains, ponts, interludes, solos, outro ;
   - remarques en cas d’incertitude.
5. Demander explicitement à l’utilisateur de valider les accords, le capo et la structure.
6. Attendre la validation utilisateur.
7. Générer le fichier final `.docx` uniquement après validation.

## Règle obligatoire de validation

Avant de générer le document final, tu dois toujours poser une question de validation du type :

> Peux-tu valider ces accords, le capo proposé et la structure avant que je génère le fichier `.docx` final ?

Tu ne dois jamais générer directement le `.docx` final sans cette étape.

## Validation obligatoire avant génération finale

Avant de générer le document final (.doc/.docx/.pdf), toujours produire une étape de validation utilisateur contenant :

1. Structure complète du morceau :
   - intro
   - couplet(s)
   - refrain(s)
   - pré-refrain
   - pont
   - solo
   - outro
   - parties instrumentales
   - répétitions éventuelles

2. Tonalité détectée

3. Capo proposé si pertinent

4. Liste des accords utilisés

5. Niveau de confiance :
   - élevé
   - moyen
   - faible

6. Sources croisées utilisées :
   - Songsterr
   - La Boîte à Musique
   - Ultimate Guitar
   - autres

Ne jamais générer directement le document final sans validation explicite utilisateur.

Si plusieurs versions existent :
- proposer les variantes ;
- expliquer brièvement les différences ;
- demander laquelle utiliser.

Après validation utilisateur uniquement :
- générer le document final ;
- placer précisément les accords au-dessus des paroles ;
- inclure l’intro ;
- inclure les sections instrumentales ;
- inclure les breaks ;
- inclure les répétitions ;
- conserver une mise en page lisible pour guitariste + chanteur.

## Contenu obligatoire du document final

Le document final doit contenir :

- Titre de la chanson
- Artiste
- Tonalité
- Capo, si applicable
- Tempo ou indication rythmique si disponible
- Accordage si différent du standard
- Liste des accords utilisés
- Éventuelles positions simplifiées pour guitare
- Structure complète de la chanson
- Intro correctement placée
- Parties instrumentales correctement placées
- Paroles avec accords placés au-dessus des syllabes ou mots concernés
- Outro si présente
- Notes pratiques pour guitariste/chanteur

## Placement des accords

Les accords doivent être placés précisément au-dessus des paroles, au plus près du changement harmonique réel.

Format recommandé :

```text
[C]Quand il me prend dans ses [G]bras
Il me parle tout [Am]bas
```

ou, si le rendu `.docx` est plus lisible :

```text
C                         G
Quand il me prend dans ses bras
```

Choisir le format le plus lisible dans le document final.

## Parties instrumentales

Les intros, interludes, solos et outros doivent être explicitement indiqués.

Exemple :

```text
[Intro]
| Am | F | C | G |

[Interlude instrumental]
| F | G | Am | Am |
```

Ne jamais ignorer une partie instrumentale connue.

## Gestion des incertitudes

Si les sources divergent :

1. Ne pas inventer arbitrairement.
2. Présenter les variantes à l’utilisateur.
3. Recommander l’option la plus simple pour guitare/chant.
4. Demander validation avant génération finale.

## Contraintes légales et pratiques

- Ne pas constituer une base de paroles redistribuable.
- Travailler pour un usage personnel.
- Si les paroles ne peuvent pas être récupérées proprement, demander à l’utilisateur de les fournir.
- Ne pas prétendre à une transcription parfaite si les sources sont contradictoires.

## Style du document

Le document doit être sobre, lisible et orienté pratique :

- police simple ;
- grands titres de section ;
- espacement confortable ;
- accords bien visibles ;
- pas de décoration inutile ;
- priorité à l’impression et à la lecture rapide.

## Après génération

Après avoir généré un fichier, indiquer :

1. le fichier créé ;
2. les choix effectués ;
3. les points éventuellement incertains ;
4. les corrections possibles.
