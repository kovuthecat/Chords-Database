# PROJECT_BRIEF.md

## Objectif du projet

Créer des fichiers de chords au format document pour guitariste et chanteur, à partir du titre d’une chanson fourni par l’utilisateur.

Le résultat attendu est un document lisible, imprimable et directement utilisable en répétition ou en accompagnement chant/guitare, avec les accords placés précisément au-dessus des paroles, ainsi que l’intro, les interludes, les solos, les ponts et les parties instrumentales correctement indiqués.

## Usage prévu

- Usage personnel : oui
- Usage local : oui
- Déploiement prévu : non par défaut
- Utilisateurs autres que moi : possible, mais non prioritaire

## Fonctionnalités MVP

1. Recevoir le titre d’une chanson et, si nécessaire, l’artiste.
2. Rechercher les accords et la structure depuis des sources publiques pertinentes, par exemple Songsterr, La Boîte à Musique, Ultimate Guitar, Chordify ou autres sources fiables.
3. Produire un fichier `.docx` contenant :
   - titre ;
   - artiste ;
   - tonalité estimée ou source ;
   - capo si pertinent ;
   - accords utilisés ;
   - paroles avec accords positionnés ;
   - intro ;
   - couplets ;
   - refrains ;
   - ponts ;
   - parties instrumentales ;
   - outro ;
   - notes utiles pour guitare/chant.

## Règle produit obligatoire

Avant toute génération finale de document, Claude Code doit toujours demander explicitement à l’utilisateur de valider :

1. les accords retenus ;
2. la tonalité ;
3. le capo proposé, si besoin ;
4. la structure globale de la chanson.

Aucun fichier final `.docx` ne doit être généré avant cette validation.

## Hors périmètre v1

- Génération automatique d’un arrangement avancé.
- Transcription audio complète depuis un fichier son.
- Gestion multi-instruments complexe.
- Base de données locale de chansons.
- Interface graphique complète.
- Publication ou redistribution de paroles protégées.

## Contraintes importantes

- Les fichiers sont destinés exclusivement à un usage guitariste + chanteur.
- Priorité à la lisibilité et à la précision du placement des accords.
- Ne pas sur-ingénier : un script simple ou un workflow manuel assisté suffit pour commencer.
- Toujours distinguer brouillon de validation et document final.
- Respecter les limites légales : ne pas créer une base de paroles redistribuable ; privilégier un usage personnel et des sources fournies/validées par l’utilisateur.

## Format de sortie cible

Format principal : `.docx`

Optionnel : `.md` intermédiaire pour faciliter relecture, correction et versioning Git.
