# Watch Selection

Application personnelle pour gérer ma collection de montres « rêvée » : collection par famille (GADA, Dress,
Chrono, Field, Diver…), liste complète, fiches détaillées, notes perso, indice poignet, et ajout de nouvelles
montres assisté par IA.

## État

**Étape 0 — conception.** Rien n'est encore développé.

- [`docs/CONCEPTION.md`](docs/CONCEPTION.md) — options techniques, choix recommandés, modèle de données, plan par étapes, questions ouvertes
- [`mockups/maquette.html`](mockups/maquette.html) — maquette cliquable (ouvrir dans un navigateur, aucun serveur nécessaire)

## Principes

- Le plus simple possible : un `index.html` (HTML/CSS/JS natif, sans librairie ni build) + un `watches.json`.
- Un unique `api.php` optionnel pour sauvegarder sur le serveur et appeler l'IA (la clé API ne quitte jamais le serveur).
- Liens externes toujours ouverts dans un nouvel onglet.
