# Watch Selection — Document de conception

> Statut : **étape 0 — conception & maquettes (v2)**. Rien n'est encore développé.
> Maquette cliquable : [`mockups/maquette.html`](../mockups/maquette.html) (ouvrir dans un navigateur).

## 1. Ce que l'application doit faire

| # | Besoin | Écran |
|---|--------|-------|
| 1 | Voir la **collection rêvée** par famille, la montre détourée en très grand | **Collection** |
| 2 | Dans chaque famille, **parcourir les alternatives** et en promouvoir une en un clic | **Collection** (rangée de vignettes) |
| 3 | La **liste complète**, filtrable et triable | **Catalogue** (galerie ou tableau) |
| 4 | Une **fiche détaillée** : photos jour/nuit, **variantes de couleur à faire défiler**, avis, points forts/faibles, liens | **Fiche** |
| 5 | **Ajouter une montre** par nom ou lien ; l'IA cherche les infos et la classe | **Ajouter** |
| 6 | Mes **notes personnelles** | **Fiche** |
| 7 | Un **indice poignet** (18 cm) | Partout |
| 8 | Liens externes dans un **nouvel onglet** ; le site **ne dépend pas** des pages en ligne pour s'afficher | Partout |

## 2. Décisions prises (réponses du 02/10/2026)

| Sujet | Décision |
|---|---|
| Hébergement | Homelab ; le projet doit rester **très simple** |
| Accès | Protégé par **Pangolin** en amont → l'application ne gère **aucune authentification** |
| IA | **Indépendante du fournisseur** : ChatGPT, Claude, Mistral, local… via une API standard |
| Familles | Une montre peut appartenir à **plusieurs familles** ; liste élargie proposée §7 |
| Statuts | principal / alternative / piste future / écartée / **possédée** |
| Variantes | Une seule fiche par montre ; **je choisis ma couleur préférée** (c'est elle qui s'affiche dans la collection) ; dans la fiche on **fait défiler les variantes** |
| Images | **Copiées localement** (et détourées) : le site s'affiche même si les sites des marques changent |
| Textes de la v27 | Pas repris tels quels, mais **mes critères** en sont extraits pour guider l'IA (§6) |
| Visuel | Moderne, luxe, dépouillé ; montre **détourée en grand** comme élément principal (§8) |

---

## 3. Architecture

```
watch-selection/
├── index.html          ← toute l'application (HTML + CSS + JS natif, sans librairie ni étape de build)
├── api.php             ← un seul fichier : lire/écrire les données, appeler l'IA, télécharger les photos
├── config.php          ← URL + clé + modèle de l'IA, moteur de recherche (jamais commité)
├── data/watches.json   ← les données (une montre = un objet) + sauvegardes automatiques datées
├── img/                ← photos détourées (PNG/WebP), une sous-dossier par montre
└── docker-compose.yml  ← 10 lignes : image officielle php:apache + un volume
```

**Pourquoi PHP ?** C'est la seule technologie qui permet « un fichier = un point d'API » sans framework, sans
dépendances, sans process à gérer : Apache exécute `api.php` à la demande. Dans le homelab, c'est un conteneur
officiel `php:8-apache` qui monte le dossier ; on le place derrière Pangolin comme les autres services.

**Pas d'authentification dans l'application** : Pangolin s'en charge. `api.php` n'écoute que ce que le
reverse-proxy lui transmet.

**Sauvegarde** : à chaque écriture, l'ancien `watches.json` est conservé (`data/backup/watches-AAAAMMJJ-HHMMSS.json`,
les 50 dernières versions). Le dossier entier se sauvegarde comme n'importe quel volume du homelab.

**Pourquoi pas de framework (React, Vue…) ?** Pour ~50 à 200 montres et 4 écrans, du JavaScript natif suffit, se
relit sans outillage et ne casse pas avec le temps.

---

## 4. L'ajout « intelligent » d'une montre — indépendant du fournisseur d'IA

### Le standard retenu : l'API « Chat Completions » au format OpenAI
C'est le format que parlent quasiment tous les fournisseurs et serveurs locaux : OpenAI, Mistral, Google Gemini,
DeepSeek, OpenRouter (qui donne accès à Claude, GPT, Gemini… avec une seule clé), Ollama, LM Studio, vLLM, LiteLLM.
Changer d'IA = changer 3 lignes dans `config.php` :

```php
'ai' => [
  'base_url' => 'https://api.openai.com/v1',        // ou https://openrouter.ai/api/v1, http://ollama:11434/v1 …
  'api_key'  => 'sk-…',
  'model'    => 'gpt-…',                             // ou 'anthropic/claude-…', 'mistral-large-latest', 'qwen3' …
],
```

### Le problème : la recherche web n'est pas standard
Chaque fournisseur a sa propre façon de « chercher sur le web » (quand il le propose). Pour rester agnostique,
**c'est `api.php` qui fait la recherche et lit les pages**, puis donne le texte à l'IA. L'IA n'a plus qu'à
**lire et structurer**, ce que tous les modèles savent faire, même locaux.

```
 « Hamilton Khaki Field Mechanical 38 »   ou   https://…/fiche-produit
            │
            ▼
 api.php ─① recherche ─▶ SearXNG (homelab) ou API Brave Search ─▶ 5-8 meilleurs liens
         ─② lecture   ─▶ télécharge ces pages (+ le lien donné), garde le texte utile
                         et la liste des images trouvées (og:image, galeries produit)
         ─③ IA        ─▶ /chat/completions : « voici mes critères, mes familles, ces pages ;
                         réponds avec ce JSON » → fiche + familles + statut + justification
         ─④ photos    ─▶ télécharge les photos choisies dans img/
            │
            ▼
 index.html : écran « Vérifier » — champs pré-remplis, photos proposées, familles suggérées
            │  je corrige, je valide
            ▼
 data/watches.json
```

- **Moteur de recherche** : [SearXNG](https://docs.searxng.org) se déploie en un conteneur dans un homelab et
  expose une API JSON gratuite. Alternative sans hébergement : clé API Brave Search (offre gratuite limitée).
- **Si on donne un lien**, l'étape ① sert seulement à compléter (avis, autres coloris).
- **Rien n'est enregistré sans validation.** Le JSON de l'IA est vérifié par `api.php` (types, bornes : un diamètre
  de 400 mm est rejeté).
- **« Actualiser »** sur une fiche existante relance le même circuit pour mettre à jour prix, liens et avis.
- **Coût** : selon le modèle, de 0 € (modèle local via Ollama) à quelques centimes par montre. Le nombre de jetons
  utilisés sera affiché après chaque ajout.

---

## 5. Photos : locales, détourées, avec variantes

### Copie locale
Toutes les photos sont téléchargées par `api.php` dans `img/<id-montre>/`. Le site n'affiche **jamais** une image
distante. Les liens vers les sites des marques restent, mais seulement comme liens cliquables.

### Détourage
Objectif : la montre « posée » sur le fond de l'application, sans rectangle blanc autour.

| Méthode | Quand | Coût |
|---|---|---|
| **a. Photo déjà détourée** (PNG transparent) | Beaucoup de fiches officielles en proposent ; l'IA est priée de les préférer | rien |
| **b. Détourage automatique dans le navigateur** au moment de l'ajout (librairie `@imgly/background-removal`, modèle d'IA exécuté localement par le navigateur), résultat envoyé à `api.php` en PNG | Photos sur fond uni ou studio | aucun serveur supplémentaire ; ~quelques secondes par photo |
| **c. Fondu CSS** (`mix-blend-mode: multiply`) | Filet de sécurité : un fond blanc devient invisible sur le fond pierre de l'application | rien |

Un bouton **« Détourer à nouveau »** et un **dépôt manuel** de photo (glisser-déposer) permettront de corriger les cas
ratés. La maquette contient deux vraies photos détourées (Concordia, Tsuyosa) pour juger du rendu.

### Variantes de couleur
- Une variante = `{nom, couleur, référence, photo}`.
- **Ma couleur** : un clic sur « ♡ Choisir cette couleur » dans la fiche ; c'est cette variante qui s'affiche dans la
  collection et le catalogue.
- Dans la fiche : flèches ‹ ›, pastilles, et **balayage** au doigt sur téléphone.

---

## 6. Mon profil : guider l'IA avec mes critères

Un champ « Mes critères » (texte libre, modifiable dans l'application) est envoyé à l'IA à chaque recherche. Elle
s'en sert pour classer la montre, proposer un statut et écrire une ligne **« Adéquation à ma collection »**.
Première version, extraite de la v27 :

> - Collection **petite, cohérente, variée et abordable** : chaque montre apporte quelque chose que les autres n'ont
>   pas (une technologie, une histoire, un mouvement, un design ou un usage). Éviter les doublons d'usage.
> - **Budget** cœur de cible 200–800 € ; au-delà, seulement pour une pièce vraiment singulière.
> - **Mouvements variés** : solaire, radio-piloté, quartz haute précision, automatique, manuel.
> - **Élégance et discrétion** : cadrans propres, index bâtons ou fins, peu d'écritures ; pas de cadran gadget.
> - **Couleurs** : fonctionnelles sobres ; la couleur est réservée au chrono et au sport-chic ; exceptions assumées
>   quand le cadran est la raison d'être de la montre.
> - **Poignet 18 cm** : diamètre idéal 36–40 mm, épaisseur idéalement ≤ 10–11 mm, entre-cornes ≤ 48 mm ;
>   au-delà de 43 mm « à essayer impérativement ».
> - Appréciés : **saphir**, **20 mm standard** (changer de bracelet facilement), sans date ou date discrète,
>   bonne lisibilité nocturne.
> - **Disponibilité** : préciser UE officiel / import Japon / import direct et les frais à prévoir.

## 7. Familles

Une montre peut être dans plusieurs familles ; chaque famille a un **choix principal** et un court texte
« rôle dans la collection ». Les familles sont modifiables dans l'application. Proposition :

| Famille | Rôle | Statut |
|---|---|---|
| **GADA** | Go-anywhere-do-anything, set-and-forget | v27 |
| **Beater / Digitale** | L'outil qu'on porte sans précaution | v27 |
| **Dress** | Fine, épurée, pour les occasions | v27 |
| **Chronographe** | Mesure du temps, plaisir mécanique | v27 |
| **Sport-chic intégré** | Bracelet intégré, graphique | v27 |
| **Diver** | Lunette tournante, étanchéité ≥ 200 m | v27 (séparée de Tool) |
| **Field** | Lisibilité militaire, sobriété | v27 |
| Pilote | Grands chiffres, grande couronne, lisibilité | nouvelle |
| GMT / Voyage | Deuxième fuseau horaire | nouvelle |
| Outdoor / Tool | Boussole, altimètre, exploration (Pro Trek…) | nouvelle (ex « Toolwatch ») |
| Pièce d'art | Cadran artisanal ou design singulier (urushi, feuille d'argent, Beaubleu…) | nouvelle, inspirée de la v27 |

Les familles « classiques » citées par les guides horlogers sont plongée, field, pilote, GMT, dress et chronographe
([Monochrome](https://monochrome-watches.com/watch-styles/), [Outlook Luxe](https://luxe.outlookindia.com/watches-jewellery/watches/different-watch-styles-explained-a-complete-guide-to-popular-watch-types)) ;
pilote et GMT manquaient à ta liste.

---

## 8. Direction visuelle

**« Showroom »** : fond pierre très clair, beaucoup de vide, la montre détourée comme unique élément fort.

- **Typographie** : grandes capitales fines (Cormorant Garamond, sérif à fort contraste) pour les noms ; petites
  capitales très espacées (Inter) pour les libellés. Les polices seront **copiées localement** (2 fichiers) pour
  rester indépendant d'Internet.
- **Couleurs** : noir encre, gris chaud, un seul accent champagne ; vert/ambre/rouge discrets pour l'indice poignet.
- **Collection** : une famille = un écran. Nom de famille géant en filigrane derrière la montre, ombre portée douce,
  extrémités du bracelet en fondu. À gauche, nom et accroche ; à droite, caractéristiques séparées par des filets ;
  en bas, les alternatives façon configurateur. Index discret des familles à gauche.
- **Fiche** : la montre occupe la moitié gauche (fixe au défilement) ; **« Nuit »** fait passer le fond au noir
  pour la vue nocturne.
- **Animations** : fondus et légers glissements, rien de démonstratif.

## 9. Modèle de données (une montre)

```jsonc
{
  "id": "citizen-tsuyosa-nj0150",
  "brand": "Citizen", "model": "Tsuyosa", "reference": "NJ0150-81Z",
  "tagline": "La couleur et le bracelet intégré, en toute simplicité.",
  "categories": ["sport"],                        // plusieurs familles possibles
  "status": "alternative",                        // alternative | future | ecartee | possedee  (« principal » est déduit)
  "specs": { "diameter": 40, "thickness": 11.7, "lugToLug": 45.5, "lugWidth": null,
             "movement": "Automatique", "caliber": "8210", "crystal": "Saphir", "case": "Acier",
             "water": "50 m", "weight": null, "lume": "…", "date": "Guichet à 3 h" },
  "price": { "min": 299, "max": 299, "currency": "EUR", "note": "UE officiel" },
  "variants": [
    { "name": "Jaune",     "color": "#e5a91e", "ref": "NJ0150-81Z", "image": "img/citizen-tsuyosa-nj0150/jaune.png" },
    { "name": "Turquoise", "color": "#43b3ae", "ref": "NJ0151-88M", "image": "img/…/turquoise.png" }
  ],
  "favoriteVariant": 0,                           // « ma couleur »
  "images": { "night": "img/…/nuit.png", "wrist": ["img/…/porte-1.jpg"] },
  "pros": ["…"], "cons": ["…"],
  "reviews": "Synthèse des avis…",
  "fit": "Adéquation à ma collection (écrite par l'IA, modifiable)",
  "links": [ { "label": "Fiche officielle", "url": "https://…" } ],
  "notes": "Mes notes",
  "added": "2026-10-02", "updated": "2026-10-02"
}
```

En tête du fichier : `profile` (§6), `wrist: {circumference: 18}`, `categories: [{id, label, role, pick}]`.
Le choix principal est stocké dans la famille (`pick`) : promouvoir une alternative = changer une valeur.

## 10. Indice poignet

Pour 18 cm, le dessus du poignet mesure ~51 mm. La donnée la plus parlante est l'**entre-cornes** :

| Entre-cornes | Verdict |
|---|---|
| < 42 mm | Petite |
| 42 – 50 mm | Idéal |
| 50 – 52 mm | Bien |
| 52 – 54 mm | Limite — à essayer |
| > 54 mm | Grande |

−1 niveau si épaisseur > 13 mm ; entre-cornes inconnu → estimé à diamètre × 1,2. Tour de poignet réglable.

## 11. Plan de développement

| Étape | Contenu |
|---|---|
| **0** | Conception + maquettes ✔ |
| **1** | `index.html` + `api.php` (lecture/écriture) + `docker-compose.yml`. **Conversion de la v27** (41 montres) avec copie et détourage des photos. Collection, Catalogue, Fiche, notes, choix principal, ma couleur |
| **2** | Ajout / actualisation par IA (recherche SearXNG ou Brave + n'importe quelle API compatible OpenAI), écran de vérification, détourage à l'import, dépôt manuel de photos |
| **3** | Finitions : édition des familles et du profil, comparaison côte à côte, export d'une version HTML autonome, installation sur l'écran d'accueil du téléphone |

## 12. Questions restantes

1. As-tu (ou veux-tu) **SearXNG** dans le homelab, ou préfères-tu une clé **Brave Search** ?
2. Avec quel fournisseur d'IA veux-tu tester en premier (OpenAI, OpenRouter, Ollama local…) ?
3. La **liste de familles** du §7 te convient-elle ? Garder Pilote / GMT / Pièce d'art ?
4. Le **profil** du §6 te ressemble-t-il ? (corrige librement)
5. La **direction visuelle** de la maquette v2 : on part là-dessus ?
