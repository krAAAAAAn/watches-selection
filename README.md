# Watch Selection

Application personnelle pour gérer ma collection de montres « rêvée » : une famille par écran (GADA, Dress,
Chrono, Field, Diver…) avec la montre détourée en grand, un catalogue complet, des fiches détaillées, mes notes,
mes couleurs préférées et un indice d'adéquation au poignet.

**État : étape 1 terminée** — l'application complète, sans IA. L'ajout automatique par IA est l'étape 2
(voir [`docs/CONCEPTION.md`](docs/CONCEPTION.md)).

## Contenu du dépôt

```
app/                    ← le site (c'est ce dossier qui est servi)
├── index.html          ← toute l'application : HTML + CSS + JavaScript, sans librairie
├── api.php             ← lecture / écriture des données, rapatriement et dépôt des photos
├── fonts/              ← polices locales (Cormorant Garamond, Inter — licence OFL)
├── seed/               ← données de départ : les 44 montres de la v27 (+ 2 photos déjà détourées)
├── data/               ← (créé au 1er lancement) watches.json + backup/ — NON versionné
└── img/                ← (créé au 1er lancement) photos rapatriées / détourées — NON versionné
docker-compose.yml      ← conteneur php:apache officiel
docker/php.ini          ← limites d'envoi de photos
tools/import_v27.py     ← conversion (déjà faite) du magazine v27 vers app/seed/watches.json
docs/CONCEPTION.md      ← choix techniques, modèle de données, feuille de route
mockups/                ← maquettes de conception (historique)
```

## Installation dans le homelab

```bash
git clone <ce dépôt> watch-selection && cd watch-selection
docker compose up -d          # → http://<serveur>:8080
```

Puis déclarer `http://<serveur>:8080` comme ressource dans **Pangolin** (c'est lui qui protège l'accès ; l'application
n'a volontairement pas d'authentification).

### Premier lancement (une seule fois)

1. Ouvrir le site : les 44 montres sont là, avec des photos encore chargées depuis les sites des marques.
2. **Réglages** (icône à curseurs en haut à droite) → **« 1 · Rapatrier les photos »** : le serveur télécharge toutes
   les photos dans `app/img/`. Les échecs (site disparu, blocage) sont listés ; on les corrige ensuite fiche par fiche
   (*Modifier → Photos → Depuis une URL* ou *Fichier*).
3. **« 2 · Détourer celles sur fond uni »** : retire automatiquement le fond des photos de studio (fond blanc, gris
   ou noir). Les photos à fond non uni sont laissées telles quelles et restent lisibles grâce au fondu du site.
4. Parcourir la collection et retoucher au besoin : *Modifier → Photos → Détourer* ouvre un aperçu avec réglage de
   la tolérance, et permet de revenir à l'original.

### Sans Docker (test rapide sur un PC)

```bash
php -S 127.0.0.1:8080 -t app       # PHP 8 avec l'extension curl
```

## Utilisation

| Je veux… | Où |
|---|---|
| Changer le choix principal d'une famille | Collection → cliquer une vignette en bas → **★ En faire mon choix** |
| Choisir ma couleur préférée | Fiche → flèches ‹ › (ou ← → au clavier, ou glisser au doigt) → **♡ Choisir cette couleur** |
| Voir la vue de nuit | Fiche → **Nuit** |
| Ajouter / retirer une famille, changer le statut | Fiche → libellés des familles en haut à droite, menu de statut sous le prix |
| Écrire mes notes | Fiche → **Mes notes** (enregistrement automatique) |
| Ajouter une montre | **+** en haut à droite (saisie manuelle pour l'instant) |
| Modifier familles, tour de poignet, mes critères | **Réglages** |
| Exporter / importer toutes les données | **Réglages → Données** |

## Données et sauvegardes

- Tout est dans `app/data/watches.json` (texte lisible) et `app/img/`. Sauvegarder ces deux dossiers suffit.
- À chaque modification, l'ancienne version est copiée dans `app/data/backup/` (les 50 dernières sont gardées).
- Mettre à jour l'application (`git pull`) ne touche jamais aux données : `data/` et `img/` ne sont pas versionnés.
- `app/seed/` ne sert qu'au tout premier lancement (si `data/watches.json` n'existe pas encore).

## Principes

- Le plus simple possible : un fichier HTML, un fichier PHP, un conteneur officiel. Aucune librairie, aucun `npm`.
- Indépendant d'Internet pour s'afficher : photos et polices sont locales. Les liens vers les sites des marques
  restent cliquables et s'ouvrent dans un nouvel onglet.
