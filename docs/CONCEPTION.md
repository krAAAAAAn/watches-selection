# Watch Selection — Document de conception

> Statut : **étape 0 — conception & maquettes** (rien n'est encore développé).
> Maquette cliquable : [`mockups/maquette.html`](../mockups/maquette.html).

## 1. Ce que l'application doit faire (reformulation)

| # | Besoin | Écran |
|---|--------|-------|
| 1 | Voir la **collection rêvée** par famille (GADA, Field, Chrono, Dress, Diver…), la photo de la montre au centre | **Collection** |
| 2 | Dans chaque famille, **parcourir les alternatives** et en promouvoir une en « choix principal » en un clic | **Collection** (bandeau horizontal) |
| 3 | La **liste complète** avec les caractéristiques principales, filtrable et triable | **Liste** |
| 4 | Une **fiche détaillée** : photos, variantes de couleur, vue nocturne, avis, points forts/faibles, liens | **Fiche** |
| 5 | **Ajouter une montre** en donnant un nom ou un lien ; l'IA cherche les infos et propose la/les catégories | **Ajouter** |
| 6 | Mes **notes personnelles** sur chaque montre | **Fiche** |
| 7 | Un **indice de cohérence poignet** (18 cm) | Partout (pastille) |
| 8 | Liens externes ouverts dans un **nouvel onglet** | Partout |

Contraintes : le plus autonome possible (un fichier sur un serveur, pas de dépendances système), joli, simple.

---

## 2. Le choix structurant : où vivent les données ?

Une page HTML seule sait **afficher** mais ne sait pas **enregistrer** sur le serveur ni garder secrète une clé d'API.
Dès qu'on veut modifier (notes, choix principal, ajout de montres) depuis n'importe quel appareil, il faut un petit
quelque chose côté serveur. Les options :

| Option | Comment | + | − |
|---|---|---|---|
| **A. HTML seul + stockage navigateur** | Données dans `localStorage`, export/import d'un fichier JSON | Zéro serveur | Données coincées dans *un* navigateur ; pas de synchro PC/téléphone ; pas d'IA sans exposer la clé |
| **B. HTML + 1 fichier PHP** ⭐ | `index.html` + `watches.json` + `api.php` (~100 lignes) | PHP existe sur quasiment tout hébergement mutualisé (OVH, o2switch, Infomaniak, Synology…) ; rien à installer ; la clé IA reste sur le serveur | Nécessite un hébergement avec PHP |
| C. GitHub comme base de données | Page sur GitHub Pages, sauvegarde par commit via l'API GitHub | Historique de chaque modif, gratuit | Jeton GitHub dans le navigateur, délai de publication ~1 min, IA toujours sans serveur pour la clé |
| D. Petit serveur (Node, Python, PocketBase…) | Un process qui tourne en continu | Très flexible | Il faut un VPS, un process à surveiller, des mises à jour → contraire à « keep it simple » |
| E. Service cloud (Supabase, Firebase) | Base hébergée | Robuste | Compte tiers, SDK, dépendance externe |

**Recommandation : B**, avec un **mode dégradé A** intégré gratuitement : si `api.php` est absent (ou si on ouvre
le fichier en local), l'application fonctionne quand même en lecture + modifications dans le navigateur, avec un
bouton « Exporter le JSON ».

### Arborescence cible

```
montres/
├── index.html      ← toute l'application (HTML + CSS + JS « vanilla », aucune librairie, aucun build)
├── watches.json    ← les données (une montre = un objet)
├── api.php         ← (étapes 2-3) sauvegarde + appel IA ; protégé par mot de passe
├── config.php      ← clé API + mot de passe (jamais commité)
└── img/            ← photos téléchargées localement (fini les liens d'images cassés)
```

Pourquoi séparer `index.html` et `watches.json` plutôt que tout mettre dans un seul fichier ?
Parce qu'on peut alors faire évoluer l'application sans toucher aux données (et inversement). Un bouton
« **Exporter une version autonome** » pourra quand même générer un HTML unique avec les données dedans,
pour l'emporter hors ligne ou le partager — comme ton magazine actuel.

### Pourquoi pas de framework (React, Vue…) ?
Pour ~50 à 200 montres et 4 écrans, du JavaScript natif suffit largement, se lit sans outillage et ne
« pourrit » pas avec le temps (pas de `npm install` qui casse dans 3 ans). C'est la solution la plus simple.

---

## 3. L'ajout « intelligent » d'une montre

### Principe
```
 Toi : « Seiko Astron SBXY031 »  ou  https://…/fiche-produit
        │
        ▼
 index.html ──POST──▶ api.php ──▶ API Claude (avec outils web_search + web_fetch)
                                     │  cherche fiche constructeur, revendeurs, reviews
                                     │  renvoie un JSON au format de watches.json
        ◀───────── proposition ──────┘
        │
        ▼
 Écran « Vérifier » : tous les champs pré-remplis + catégories proposées + photos trouvées
        │  tu corriges si besoin, tu valides
        ▼
 api.php enregistre dans watches.json et télécharge les photos dans img/
```

- **Nom ou lien, même bouton** : si c'est une URL, l'IA lit d'abord la page, puis complète par une recherche.
- **Classement automatique** : l'IA reçoit la liste de tes catégories et la description de ta collection actuelle ;
  elle propose 1 à 2 catégories et un statut (« alternative » par défaut), avec une phrase de justification.
- **Toujours une étape de validation** : l'IA peut se tromper (dimensions, prix) ; rien n'est enregistré sans ton OK.
- **Bouton « Rafraîchir »** sur chaque fiche : relance l'IA pour mettre à jour prix/liens/avis d'une montre existante.
- **Fiche produit seule, sans IA ?** Techniquement possible (lire les balises `og:image`, `og:title`, données
  `schema.org/Product` de la page), mais les sites horlogers mettent rarement les dimensions dans des balises
  standard → résultat pauvre. L'IA avec recherche web fait les deux mieux. On ne garde donc **qu'une voie**.

### Coût et prérequis
- Une **clé API Anthropic** (console.anthropic.com), paiement à l'usage. Ce n'est pas l'abonnement Claude.ai.
- Ordre de grandeur estimé : **quelques dizaines de centimes par montre ajoutée** (recherche web + lecture de
  plusieurs pages). À mesurer à l'étape 3 ; on affichera le coût réel de chaque ajout.
- La clé reste dans `config.php` sur ton serveur, jamais dans le navigateur.

### Plan B sans clé API
Bouton « Copier le prompt » : l'app génère la demande, tu la colles dans Claude.ai, tu recolles le JSON obtenu.
C'est ce que tu fais aujourd'hui, mais en 2 copier-coller au lieu de réécrire tout le magazine. À n'utiliser que
si tu ne veux pas de clé API.

---

## 4. Modèle de données (une montre)

```jsonc
{
  "id": "seiko-sbxy031",
  "brand": "Seiko", "model": "Astron", "reference": "SBXY031",
  "tagline": "Le GADA titane au cadran bleu ondulé",
  "categories": ["gada"],             // une montre peut être dans plusieurs familles
  "status": "alternative",            // principal | alternative | future | ecartee | possedee
  "specs": {
    "diameter": 39, "thickness": 9.6, "lugToLug": 46.5, "lugWidth": 20,
    "movement": "Solaire radio-piloté", "caliber": "7B72",
    "crystal": "Saphir", "case": "Titane", "water": "10 bar", "weight": 80,
    "lume": "LumiBrite", "functions": ["calendrier perpétuel", "radio"]
  },
  "price": { "min": 450, "max": 550, "currency": "EUR", "note": "import Japon" },
  "availability": "Import JDM",
  "images": [
    { "src": "img/seiko-sbxy031-1.jpg", "kind": "day" },
    { "src": "img/seiko-sbxy031-night.jpg", "kind": "night" }
  ],
  "variants": [ { "name": "Bleu", "color": "#1f3b6d", "ref": "SBXY031", "image": "img/…" } ],
  "pros": ["…"], "cons": ["…"],
  "reviews": "Synthèse des avis pros & amateurs…",
  "links": [ { "label": "Fiche officielle", "url": "https://…" }, { "label": "Review Fratello", "url": "…" } ],
  "notes": "Mes notes perso (texte libre)",
  "added": "2026-10-01", "updated": "2026-10-01"
}
```

Et en tête de fichier, la configuration :

```jsonc
{
  "wrist": { "circumference": 18 },
  "categories": [
    { "id": "gada", "label": "GADA", "pick": "seiko-sbtm321", "order": 1 },
    { "id": "beater", "label": "Beater / outil", "pick": "casio-gw-m5610u", "order": 2 },
    …
  ],
  "watches": [ … ]
}
```

Le « choix principal » d'une famille est stocké au niveau de la **catégorie** (`pick`) : promouvoir une
alternative = changer une seule valeur. Le statut `principal` est donc déduit, pas saisi.

---

## 5. Indice de cohérence poignet

Pour un poignet de 18 cm, la face supérieure plate mesure environ 50–52 mm. La donnée la plus parlante est
l'**entre-cornes** (lug-to-lug) : s'il dépasse la largeur du poignet, la montre déborde.

| Entre-cornes | Verdict |
|---|---|
| < 42 mm | Petite (vintage, peut paraître menue) |
| 42 – 50 mm | ●●●●● Idéal |
| 50 – 52 mm | ●●●● Bien |
| 52 – 54 mm | ●●● Limite — à essayer |
| > 54 mm | ●● Trop grande probablement |

Ajustements : −1 point si épaisseur > 13 mm ; si l'entre-cornes est inconnu, estimation par diamètre × 1,2.
La règle et les seuils seront **réglables** (tour de poignet dans la config) — c'est un repère, pas une vérité :
un bracelet intégré ou des cornes très tombantes changent le porté.

---

## 6. Écrans (voir la maquette)

1. **Collection** — une « scène » par famille : grande photo du choix principal, nom, 5–6 caractéristiques clés,
   pastille poignet, prix. Sous la photo, un **carrousel horizontal** des autres montres de la famille ; un clic
   sur ★ en fait le choix principal (animation d'échange). Navigation par onglets de familles en haut.
2. **Liste** — toutes les montres en tableau compact (vignette, modèle, familles, statut, Ø/épaisseur/entre-cornes,
   mouvement, prix, poignet). Recherche texte, filtres par famille/statut/mouvement, tri par colonne.
3. **Fiche** — galerie (jour / nuit / porté), pastilles de couleur qui changent la photo, tableau technique,
   « pourquoi c'est bien / moins bien », synthèse des avis, liens (nouvel onglet), **mes notes** (sauvegarde auto),
   familles et statut modifiables, bouton « Rafraîchir avec l'IA ».
4. **Ajouter** — un seul champ « nom ou lien », progression visible, puis formulaire de vérification pré-rempli.

Style : on reprend l'esprit « magazine » de ta v27 (papier crème, typo serif, bleu ardoise / bronze), avec un
mode sombre automatique. Responsive (utilisable sur téléphone).

---

## 7. Plan de développement par étapes

| Étape | Contenu | Livrable |
|---|---|---|
| **0** | Conception + maquettes | ce document, `mockups/maquette.html` |
| **1** | Application en lecture + modifications locales. **Conversion de ta v27** (41 montres) en `watches.json`. Écrans Collection, Liste, Fiche. Notes / choix principal dans le navigateur + export JSON | `index.html`, `watches.json` |
| **2** | Sauvegarde serveur (`api.php` + mot de passe), téléchargement des images dans `img/` | `api.php` |
| **3** | Ajout et rafraîchissement par IA (nom ou lien), classement automatique | `api.php` (+ partie IA) |
| **4** | Finitions selon tes envies : comparaison côte à côte, export HTML autonome, installation sur l'écran d'accueil du téléphone… | — |

Chaque étape est utilisable en soi.

---

## 8. Questions ouvertes (à trancher avant l'étape 1)

1. **Hébergement** : quel serveur as-tu ? A-t-il PHP ? (sinon : GitHub Pages / option C, ou NAS)
2. **Accès** : site privé (mot de passe pour tout) ou lecture publique + édition protégée ?
3. **IA** : OK pour créer une clé API Anthropic payante à l'usage, ou préfères-tu le plan B (copier-coller) ?
4. **Familles** : liste définitive ? Proposition : GADA, Beater/outil, Dress, Chronographe, Sport-chic intégré,
   Diver/Tool, Field. Une montre peut-elle compter dans deux familles (ex. Concordia = Tool *et* Diver) ?
5. **Statuts** : principal / alternative / piste future / écartée / **possédée** — veux-tu suivre aussi les montres
   que tu as déjà ?
6. **Variantes** : les déclinaisons de couleur (SBTM319/321/323, NB1050-59x) = une seule fiche avec variantes
   (comme dans ta v27) ? Je le propose ainsi.
7. **Images** : OK pour les copier sur ton serveur (fiable) plutôt que pointer vers les sites (cassent souvent) ?
8. **Contenu éditorial** de la v27 (« Boussole éditoriale », textes d'intro par rôle) : à garder ? Je propose une
   phrase « rôle dans la collection » par famille, éditable.
