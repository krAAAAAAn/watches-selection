# Watch Selection — Document de conception

> Statut : **étape 1 terminée** — application complète sans IA (`app/`). Étape suivante : ajout par IA.
> Installation et utilisation : [`README.md`](../README.md). Maquettes de conception : [`mockups/`](../mockups/).

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

## 2. Décisions prises (02/10/2026)

| Sujet | Décision |
|---|---|
| Hébergement | Webapp accessible depuis PC et téléphone, données persistées, **le plus portable possible** → **un seul exécutable**, sans PHP ni Docker (§3) |
| Accès | Protégé par **Pangolin** en amont → l'application ne gère **aucune authentification** |
| IA | **Indépendante du fournisseur** (API standard) — **reportée à l'étape 2** : on valide d'abord tout le reste |
| Recherche web (pour l'IA) | **SearXNG** auto-hébergé : gratuit, sans compte (comparatif §4) |
| Familles | Plusieurs familles par montre ; ajout d'**Outdoor / Tool** et **Pièce d'art**, mais **hors de la collection** (catalogue seulement) |
| Statuts | principal / alternative / piste future / écartée / **possédée** |
| Variantes | Une seule fiche par montre ; **je choisis ma couleur préférée** (c'est elle qui s'affiche dans la collection) ; dans la fiche on **fait défiler les variantes** |
| Images | **Copiées localement** (et détourées) : le site s'affiche même si les sites des marques changent |
| Textes de la v27 | Pas repris tels quels, mais **mes critères** en sont extraits pour guider l'IA (§6) |
| Visuel | Moderne, luxe, dépouillé ; montre **détourée en grand** comme élément principal (§8) |

---

## 3. Architecture : un seul exécutable

```
watch-selection(.exe)   ← UN fichier (~8 Mo) : serveur web + toute l'application embarquée
watch-data/             ← créé à côté de lui au premier lancement
├── watches.json        ← les données (texte lisible)
├── backup/             ← les 50 versions précédentes
└── img/<id-montre>/    ← photos rapatriées, déposées ou détourées
```

Dans le dépôt :

```
main.go                 ← le serveur (Go, bibliothèque standard uniquement, ~300 lignes)
app/                    ← l'application web, embarquée dans l'exécutable à la compilation
├── index.html          ← toute l'interface (HTML + CSS + JS natif, sans librairie)
├── fonts/              ← polices locales
└── seed/               ← données de départ (44 montres de la v27) copiées au premier lancement
build.sh                ← compile pour Windows, Mac, Linux (PC, NAS, Raspberry Pi)
.github/workflows/      ← compile et publie automatiquement les exécutables sur GitHub
```

**Pourquoi un exécutable Go ?** Une webapp accessible depuis le PC et le téléphone avec des données persistées
demande un serveur. Le plus portable est un fichier unique qui *est* ce serveur : rien à installer (ni PHP, ni
Docker, ni runtime), il tourne sur n'importe quelle machine — homelab, NAS, Raspberry Pi, PC — et se met à jour en
remplaçant le fichier. Go produit ces exécutables autonomes pour tous les systèmes depuis un seul code source.
*(Une première version utilisait PHP + Docker ; abandonnée le 02/10/2026 pour cette raison.)*

**Écarté : un fichier HTML seul, sans serveur.** Les données resteraient dans un seul navigateur (pas de
synchronisation PC/téléphone), et un navigateur n'a pas le droit de télécharger les photos des sites des marques.

**Pas d'authentification dans l'application** : Pangolin s'en charge pour l'accès depuis l'extérieur. Sur le réseau
local, quiconque connaît l'adresse peut ouvrir le site (option `-host 127.0.0.1` pour n'autoriser que la machine
elle-même).

**Sauvegarde** : à chaque écriture, l'ancien `watches.json` est conservé dans `backup/` (50 dernières versions).
L'écriture est atomique (fichier temporaire puis renommage). Sauvegarder `watch-data/` suffit.

**Plusieurs appareils** : chaque version porte un numéro (`rev`). Si un appareil resté ouvert sur une ancienne
version tente d'enregistrer, le serveur refuse au lieu d'écraser les changements faits ailleurs ; l'application
recharge alors les données et prévient. En revenant sur l'onglet ou l'appli, les données sont rafraîchies.

**Une seule écriture : tout le fichier.** L'application envoie l'ensemble des données à chaque modification
(quelques centaines de Ko). C'est le plus simple et c'est sans risque pour un seul utilisateur.

**Pourquoi pas de framework (React, Vue…) ?** Pour ~50 à 200 montres et 4 écrans, du JavaScript natif suffit, se
relit sans outillage et ne casse pas avec le temps.

---

## 4. L'ajout « intelligent » d'une montre — indépendant du fournisseur d'IA

### Le standard retenu : l'API « Chat Completions » au format OpenAI
C'est le format que parlent quasiment tous les fournisseurs et serveurs locaux : OpenAI, Mistral, Google Gemini,
DeepSeek, OpenRouter (qui donne accès à Claude, GPT, Gemini… avec une seule clé), Ollama, LM Studio, vLLM, LiteLLM.
Changer d'IA = changer 3 lignes dans `watch-data/config.json` :

```jsonc
"ai": {
  "base_url": "https://api.openai.com/v1",        // ou https://openrouter.ai/api/v1, http://ollama:11434/v1 …
  "api_key":  "sk-…",
  "model":    "gpt-…"                             // ou "anthropic/claude-…", "mistral-large-latest", "qwen3" …
}
```

### Le problème : la recherche web n'est pas standard
Chaque fournisseur a sa propre façon de « chercher sur le web » (quand il le propose). Pour rester agnostique,
**c'est le serveur qui fait la recherche et lit les pages**, puis donne le texte à l'IA. L'IA n'a plus qu'à
**lire et structurer**, ce que tous les modèles savent faire, même locaux.

```
 « Hamilton Khaki Field Mechanical 38 »   ou   https://…/fiche-produit
            │
            ▼
 serveur ─① recherche ─▶ SearXNG (homelab) ou API Brave Search ─▶ 5-8 meilleurs liens
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

- **Moteur de recherche** — options comparées (octobre 2026) :

  | Option | Coût | Pour | Contre |
  |---|---|---|---|
  | **SearXNG** (auto-hébergé) ✅ retenu | **0 €** | Gratuit, sans compte, privé ; un conteneur de plus dans le homelab ; API JSON | Les moteurs interrogés peuvent ponctuellement limiter les requêtes ; activer le format `json` dans `settings.yml` |
  | Tavily | 0 € jusqu'à 1 000 recherches / mois | Conçu pour les IA, renvoie le texte des pages déjà nettoyé | Compte et clé chez un tiers |
  | Brave Search API | ~5 $ de crédit offert / mois (≈ 1 000 recherches), puis 5 $ / 1 000 | Index propre, fiable | Plus de vraie offre gratuite pour les nouveaux comptes ; carte bancaire |
  | Recherche intégrée au fournisseur d'IA | payante à l'usage | Rien à héberger | Propre à chaque fournisseur : casse l'indépendance voulue |

  Pour un usage personnel (quelques dizaines d'ajouts par mois), SearXNG et Tavily sont tous deux gratuits ;
  **SearXNG** est retenu car il ne dépend d'aucun compte. Le serveur sera écrit pour qu'on puisse basculer sur
  Tavily en changeant une ligne de configuration si SearXNG se montre capricieux.
- **Si on donne un lien**, l'étape ① sert seulement à compléter (avis, autres coloris).
- **Rien n'est enregistré sans validation.** Le JSON de l'IA est vérifié par le serveur (types, bornes : un diamètre
  de 400 mm est rejeté).
- **« Actualiser »** sur une fiche existante relance le même circuit pour mettre à jour prix, liens et avis.
- **Coût** : selon le modèle, de 0 € (modèle local via Ollama) à quelques centimes par montre. Le nombre de jetons
  utilisés sera affiché après chaque ajout.

---

## 5. Photos : locales, détourées, avec variantes

### Copie locale
Toutes les photos sont téléchargées par le serveur dans `watch-data/img/<id-montre>/`. Le site n'affiche **jamais** une image
distante. Les liens vers les sites des marques restent, mais seulement comme liens cliquables.

### Détourage
Objectif : la montre « posée » sur le fond de l'application, sans rectangle blanc autour.

| Méthode | État | Détail |
|---|---|---|
| **a. Photo déjà détourée** (PNG transparent) | ✅ | Reconnue automatiquement (bord transparent) ; seulement recadrée |
| **b. Détourage intégré** (remplissage depuis les bords) | ✅ étape 1 | Écrit en JavaScript dans `index.html`, sans librairie ni Internet. Part des bords de la photo et retire tout ce qui ressemble à la couleur du fond, adoucit le contour, recadre. Excellent sur les photos de studio à fond uni ; ne touche pas aux photos « lifestyle ». Réglages : tolérance, douceur, option « ombre portée » (désactivée par défaut car elle peut ronger l'acier poli gris). L'original est conservé : retour arrière possible |
| **c. Fondu CSS** (`mix-blend-mode: multiply`) | ✅ | Filet de sécurité : un reste de fond blanc devient invisible sur le fond pierre |
| d. Détourage par IA (modèle de segmentation) | plus tard, si besoin | Pour les photos difficiles (fond texturé). Ajouterait une dépendance : à n'envisager que si (b) ne suffit pas à l'usage |

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
« rôle dans la collection ». Une case « Collection » indique si la famille a son écran dans la collection ou
n'apparaît que comme filtre du catalogue. Tout est modifiable dans **Réglages → Familles**.

| Famille | Rôle | Statut |
|---|---|---|
| **GADA** | Go-anywhere-do-anything, set-and-forget | v27 |
| **Beater / Digitale** | L'outil qu'on porte sans précaution | v27 |
| **Dress** | Fine, épurée, pour les occasions | v27 |
| **Chronographe** | Mesure du temps, plaisir mécanique | v27 |
| **Sport-chic intégré** | Bracelet intégré, graphique | v27 |
| **Diver** | Lunette tournante, étanchéité ≥ 200 m | v27 (séparée de Tool) |
| **Field** | Lisibilité militaire, sobriété | v27 |
| Outdoor / Tool | Boussole, altimètre, exploration (Pro Trek…) | ajoutée, **hors collection** |
| Pièce d'art | Cadran artisanal ou design singulier (urushi, feuille d'argent, Beaubleu…) | ajoutée, **hors collection** |
| *Pilote, GMT / Voyage* | *non retenues pour l'instant ; ajout en 2 clics dans Réglages → Familles* | — |

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

## 9. Modèle de données

`data/watches.json` :

```jsonc
{
  "version": 1,
  "wrist": { "circumference": 18 },
  "profile": "Mes critères (texte, pour l'IA)",
  "categories": [ { "id": "gada", "label": "GADA", "role": "…", "inCollection": true, "pick": "seiko-selection-sbtm31x" } ],
  "watches": [ { /* une montre, ci-dessous */ } ]
}
```

Une montre :

```jsonc
{
  "id": "seiko-selection-sbtm31x", "brand": "Seiko", "model": "Selection SBTM31x", "reference": "les trois cadrans",
  "categories": ["gada", "dress"],
  "status": "alternative",                 // alternative | future | possedee | ecartee   (« choix principal » est déduit de categories[].pick)
  "eyebrow": "…", "headline": "Même base technique, trois tempéraments", "tagline": "…", "summary": "…",
  "style": "Dress / classique", "movement": "Solaire", "movementDetail": "Solaire • calibre 7B72", "caliber": "7B72",
  "radio": "Oui • multibande", "display": "Analogique",
  "dims": { "diameter": 39.5, "thickness": 9.5, "lugToLug": 46.1, "lugWidth": 20, "weight": 115, "integrated": false },
  "crystal": "Saphir Super-Clear", "case": "Acier inoxydable", "water": "10 bar / 100 m", "lume": "LumiBrite",
  "price": "≈ 260–320 € rendu UE*", "priceEur": 260, "availability": "Import Japon",
  "specs": [["Énergie", "Solaire • calibre 7B72"], ["Autonomie", "≈ 9 mois…"]],   // tableau complet d'origine
  "pros": ["…"], "cons": ["…"], "collectionNote": "…", "reviews": "…",
  "links": [{ "label": "Fiche principale", "url": "https://…" }],
  "photos": {
    "main":  { "src": "img/seiko-…/main-detour-….png", "original": "img/…/main-….png", "remote": ["https://…", "https://secours…"] },
    "night": null
  },
  "variants": [ { "name": "cadran bleu", "ref": "SBTM321", "color": "#24364b", "note": "…", "url": "…", "photo": { "src": null, "remote": ["…"] } } ],
  "favoriteVariant": 0,                    // « ma couleur » : c'est sa photo qui s'affiche dans la collection
  "notes": "Mes notes", "source": "v27 · page 13", "added": "…", "updated": "2026-10-02"
}
```

Une **photo** (« emplacement ») : `src` = fichier local, `remote` = adresses d'origine (essayées dans l'ordre lors du
rapatriement ; affichées provisoirement tant que `src` est vide), `original` = version avant détourage.

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

| Étape | Contenu | État |
|---|---|---|
| **0** | Conception + maquettes | ✅ |
| **1** | `index.html` + serveur (d'abord PHP, puis exécutable Go autonome). Conversion de la v27 (44 montres). Collection, Catalogue (galerie / tableau), Fiche (variantes, jour/nuit, notes), édition complète, ajout manuel, photos (rapatriement, dépôt, détourage), Réglages (familles, poignet, critères, export/import) | ✅ |
| **2** | Ajout / actualisation par IA : SearXNG + n'importe quelle API compatible OpenAI, écran de vérification | à faire |
| **3** | Finitions selon l'usage : comparaison côte à côte, export d'une version HTML autonome, installation sur l'écran d'accueil du téléphone | idées |

## 12. Points à valider (étape 1)

1. Le rendu après **rapatriement + détourage** des photos sur ton serveur (je n'ai pu le tester qu'avec les deux
   photos présentes dans la v27 : mon environnement n'a pas accès aux sites des marques).
2. Les **familles** attribuées à chaque montre lors de la conversion (modifiable en un clic dans chaque fiche).
3. L'ergonomie de l'édition et des photos, avant de brancher l'IA dessus.
