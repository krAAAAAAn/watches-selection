# Watch Selection

Application personnelle pour gérer ma collection de montres « rêvée » : collection par famille (GADA, Dress,
Chrono, Field, Diver…), liste complète, fiches détaillées, notes perso, indice poignet, et ajout de nouvelles
montres assisté par IA.

## État

**Étape 0 — conception (v2).** Rien n'est encore développé.

- [`docs/CONCEPTION.md`](docs/CONCEPTION.md) — options techniques, choix recommandés, modèle de données, plan par étapes, questions ouvertes
- [`mockups/maquette.html`](mockups/maquette.html) — maquette cliquable, direction « showroom » (ouvrir dans un navigateur, aucun serveur nécessaire)

## Principes

- Hébergé dans un homelab (conteneur `php:apache`), derrière Pangolin qui gère l'accès.

- Le plus simple possible : un `index.html` (HTML/CSS/JS natif, sans librairie ni build) + un `watches.json`.
- Un unique `api.php` pour sauvegarder, chercher sur le web et appeler l'IA — n'importe quel fournisseur compatible avec l'API OpenAI (OpenAI, OpenRouter, Mistral, Ollama…).
- Photos copiées et détourées localement : le site ne dépend pas des sites des marques pour s'afficher.
- Liens externes toujours ouverts dans un nouvel onglet.
