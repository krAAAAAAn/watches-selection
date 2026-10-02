# Watch Selection

Application personnelle pour gérer ma collection de montres « rêvée » : une famille par écran (GADA, Dress,
Chrono, Field, Diver…) avec la montre détourée en grand, un catalogue complet, des fiches détaillées, mes notes,
mes couleurs préférées et un indice d'adéquation au poignet. Accessible depuis le PC et le téléphone, données
enregistrées sur le serveur.

**Un seul fichier à lancer** — aucun PHP, Docker, Node ou autre à installer.

**État : étape 1 terminée** (application complète, sans IA). L'ajout automatique par IA est l'étape 2
(voir [`docs/CONCEPTION.md`](docs/CONCEPTION.md)).

## Installation

1. Récupérer l'exécutable de sa machine :
   - onglet **Releases** du dépôt (release « latest », publiée automatiquement depuis la branche principale), ou
   - onglet **Actions** → dernière exécution « Exécutables » → *Artifacts*, ou
   - le compiler soi-même : `./build.sh` (Go ≥ 1.22) → dossier `dist/`.

   | Machine | Fichier |
   |---|---|
   | Windows | `watch-selection-windows-amd64.exe` |
   | Mac Apple Silicon (M1…) / Intel | `watch-selection-darwin-arm64` / `-darwin-amd64` |
   | Linux PC, VM, la plupart des NAS | `watch-selection-linux-amd64` |
   | Raspberry Pi 4/5, NAS ARM récents | `watch-selection-linux-arm64` (`-linux-arm` pour les plus anciens) |

2. Le placer dans un dossier (ex. `/opt/watch-selection/`) et le lancer :

   ```bash
   chmod +x watch-selection-linux-amd64        # Linux / Mac uniquement, la première fois
   ./watch-selection-linux-amd64               # Windows : double-clic sur le .exe
   ```

   Il affiche l'adresse à ouvrir : `http://localhost:8080` sur la machine elle-même, `http://<adresse-ip>:8080`
   depuis le téléphone sur le même réseau. Les données sont créées dans `watch-data/` à côté de l'exécutable.

   Options : `-port 9000`, `-data /chemin/vers/données`, `-host 127.0.0.1` (n'accepter que la machine elle-même).

3. **Accès depuis l'extérieur** : déclarer `http://<machine>:8080` comme ressource dans **Pangolin** (c'est lui qui
   protège l'accès ; l'application n'a volontairement pas d'authentification).

### Le faire tourner en permanence (Linux, homelab)

`/etc/systemd/system/watch-selection.service` :

```ini
[Unit]
Description=Watch Selection
After=network-online.target

[Service]
ExecStart=/opt/watch-selection/watch-selection-linux-amd64 -port 8080
WorkingDirectory=/opt/watch-selection
Restart=on-failure
User=watch

[Install]
WantedBy=multi-user.target
```

```bash
sudo useradd -r watch && sudo chown -R watch /opt/watch-selection
sudo systemctl enable --now watch-selection
```

**Mettre à jour** : remplacer l'exécutable puis `sudo systemctl restart watch-selection`. Les données ne sont pas touchées.

### Premier lancement (une seule fois)

1. Ouvrir le site : les 44 montres sont là, avec des photos encore chargées depuis les sites des marques.
2. **Réglages** (icône à curseurs en haut à droite) → **« 1 · Rapatrier les photos »** : le serveur télécharge toutes
   les photos dans `watch-data/img/`. Les échecs sont listés ; on les corrige ensuite fiche par fiche
   (*Modifier → Photos → Depuis une URL* ou *Fichier*).
3. **« 2 · Détourer celles sur fond uni »** : retire automatiquement le fond des photos de studio. Les autres restent
   telles quelles et se détourent une par une (*Modifier → Photos → Détourer*, avec aperçu et retour à l'original).

## Utilisation

| Je veux… | Où |
|---|---|
| Changer le choix principal d'une famille | Collection → cliquer une vignette en bas → **★ En faire mon choix** |
| Choisir ma couleur préférée | Fiche → flèches ‹ › (← → au clavier, ou glisser au doigt) → **♡ Choisir cette couleur** |
| Voir la vue de nuit | Fiche → **Nuit** |
| Ajouter / retirer une famille, changer le statut | Fiche → libellés des familles en haut à droite, menu de statut sous le prix |
| Écrire mes notes | Fiche → **Mes notes** (enregistrement automatique) |
| Ajouter une montre | **+** en haut à droite (saisie manuelle pour l'instant) |
| Familles, tour de poignet, mes critères | **Réglages** |
| Exporter / importer toutes les données | **Réglages → Données** |

## Données et sauvegardes

- Tout est dans `watch-data/` : `watches.json` (texte lisible), `img/` (photos), `backup/` (les 50 versions
  précédentes, une par modification). Sauvegarder ce dossier suffit.
- PC et téléphone ouverts en même temps : si un appareil essaie d'enregistrer à partir de données périmées, le
  serveur refuse au lieu d'écraser, et l'application recharge les données en prévenant.

## Développement

```
main.go                 ← serveur (Go, bibliothèque standard uniquement)
app/index.html          ← toute l'interface (HTML + CSS + JS, sans librairie)
app/fonts/, app/seed/   ← polices locales, données de départ (embarquées dans l'exécutable)
tools/import_v27.py     ← conversion (déjà faite) du magazine v27 → app/seed/watches.json
docs/CONCEPTION.md      ← choix techniques, modèle de données, feuille de route
mockups/                ← maquettes de conception (historique)
```

`go run . -data ./watch-data` lance le serveur depuis les sources. L'interface est embarquée à la compilation :
relancer après chaque modification de `app/`.
