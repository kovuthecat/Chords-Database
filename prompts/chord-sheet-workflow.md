# Prompt Claude Code — Générer une fiche chords guitare/chant

Objectif :
Créer une fiche chords pour guitare et chant à partir du titre suivant :

```text
[TITRE DE LA CHANSON]
```

Artiste si connu :

```text
[ARTISTE]
```

## Étape 1 — Recherche

Recherche les informations utiles sur des sources publiques pertinentes :

- Songsterr ;
- La Boîte à Musique ;
- Ultimate Guitar ;
- Chordify ;
- autres sources fiables si nécessaire.

Compare les sources si possible.

## Étape 2 — Brouillon de validation obligatoire

Avant tout fichier final, produis uniquement un brouillon de validation contenant :

1. titre ;
2. artiste ;
3. tonalité proposée ;
4. capo proposé ou absence de capo ;
5. accordage ;
6. liste des accords utilisés ;
7. structure complète : intro, couplets, refrains, ponts, interludes, solos, outro ;
8. parties instrumentales ;
9. points d’incertitude ;
10. recommandation guitare/chant.

Puis demande explicitement :

> Peux-tu valider ces accords, le capo proposé et la structure avant que je génère le fichier `.docx` final ?

## Étape 3 — Génération finale après validation uniquement

Après validation utilisateur seulement, génère le fichier `.docx` final.

Le document doit être destiné exclusivement à un guitariste et/ou chanteur.

Il doit inclure :

- titre ;
- artiste ;
- tonalité ;
- capo ;
- accords utilisés ;
- intro ;
- couplets ;
- refrains ;
- ponts ;
- interludes ;
- solos ;
- outro ;
- paroles avec accords placés précisément ;
- notes pratiques guitare/chant.

## Contraintes

- Ne pas générer le `.docx` final sans validation.
- Ne pas ignorer les intros ou parties instrumentales.
- Ne pas inventer si les sources divergent.
- Préférer une version simple, chantable et jouable à la guitare.
- Rester sobre et lisible.
