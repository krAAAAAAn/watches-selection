#!/usr/bin/env python3
"""Convertit le magazine HTML v27 en données de départ pour l'application.

Usage :
    pip install beautifulsoup4
    python3 tools/import_v27.py Comparatif_montres_magazine_2026_collection_v27.html

Produit app/seed/watches.json (+ images embarquées dans app/seed/img/).
Script à usage unique : il documente d'où viennent les données initiales.
Les photos distantes ne sont pas téléchargées ici : l'application s'en charge
depuis le serveur (bouton « Rapatrier les photos »).
"""
import base64
import html
import json
import re
import sys
import unicodedata
from pathlib import Path

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "app" / "seed"

# --- Familles -----------------------------------------------------------------
CATEGORIES = [
    {"id": "gada",    "label": "GADA",          "role": "Set-and-forget : précise, pratique, sans friction.",           "inCollection": True},
    {"id": "beater",  "label": "Beater",        "role": "Le couteau suisse qu'on porte sans précaution.",                "inCollection": True},
    {"id": "dress",   "label": "Dress",         "role": "Moderne et épurée ; l'intérêt vient du mouvement, pas du cadran.", "inCollection": True},
    {"id": "chrono",  "label": "Chronographe",  "role": "Le plaisir mécanique, et un peu de couleur.",                   "inCollection": True},
    {"id": "sport",   "label": "Sport-chic",    "role": "Bracelet intégré, graphique et robuste.",                       "inCollection": True},
    {"id": "diver",   "label": "Diver",         "role": "L'eau et l'exploration ; le choix émotionnel assumé.",          "inCollection": True},
    {"id": "field",   "label": "Field",         "role": "Lisible, sobre, avec une idée originale.",                      "inCollection": True},
    {"id": "outdoor", "label": "Outdoor / Tool","role": "Boussole, altimètre, exploration.",                             "inCollection": False},
    {"id": "art",     "label": "Pièce d'art",   "role": "Cadran artisanal ou design singulier.",                         "inCollection": False},
]
# Choix principal par famille (numéro de page v27)
PICKS = {"gada": 13, "beater": 6, "dress": 32, "chrono": 33, "sport": 34, "diver": 35, "field": 36}

# Familles de chaque montre (numéro de page v27) — reprend la carte de collection de la v27
CATS_BY_PAGE = {
    1: ["beater"], 2: ["beater"], 3: ["beater"], 4: ["beater"], 5: ["field"], 6: ["beater"],
    7: ["field"], 8: ["dress"], 9: ["field"], 10: ["beater"], 11: ["gada", "dress"], 12: ["dress"],
    13: ["gada", "dress"], 14: ["gada"], 15: ["field", "gada"], 16: ["field"], 17: ["gada"],
    18: ["sport"], 19: ["outdoor"], 20: ["gada"], 21: ["field", "outdoor"], 22: ["dress"],
    23: ["dress"], 24: ["beater"], 25: ["chrono"], 26: ["dress"], 27: ["dress"], 28: ["gada"],
    29: ["dress"], 30: ["dress"], 31: ["dress", "gada"], 32: ["dress"], 33: ["chrono"],
    34: ["sport"], 35: ["diver", "outdoor"], 36: ["field"], 37: ["diver"], 38: ["gada"],
    39: ["sport"], 40: ["diver"], 41: ["dress", "art"],
}
TWO_WORD_BRANDS = ["Charlie Paris", "Henry Archer"]

PROFILE = """- Collection petite, cohérente, variée et abordable : chaque montre apporte quelque chose que les autres n'ont pas (une technologie, une histoire, un mouvement, un design ou un usage). Éviter les doublons d'usage.
- Budget cœur de cible 200–800 € ; au-delà, seulement pour une pièce vraiment singulière.
- Mouvements variés : solaire, radio-piloté, quartz haute précision, automatique, manuel.
- Élégance et discrétion : cadrans propres, index bâtons ou fins, peu d'écritures ; pas de cadran gadget.
- Couleurs : montres fonctionnelles sobres ; la couleur est réservée au chrono et au sport-chic ; exceptions assumées quand le cadran est la raison d'être de la montre.
- Poignet 18 cm : diamètre idéal 36–40 mm, épaisseur idéalement ≤ 10–11 mm, entre-cornes ≤ 48 mm ; au-delà de 43 mm, à essayer impérativement.
- Appréciés : saphir, entre-anses 20 mm standard, sans date ou date discrète, bonne lisibilité nocturne.
- Disponibilité : préciser UE officiel / import Japon / import direct et les frais à prévoir."""

COLOR_WORDS = [
    ("turquoise", "#3aa6a0"), ("tiffany", "#3aa6a0"), ("bleu glacier", "#9cc3d8"), ("glacier", "#9cc3d8"),
    ("bleu", "#24364b"), ("navy", "#24364b"), ("noir", "#1b1c1e"), ("black", "#1b1c1e"), ("négatif", "#2b2b2b"),
    ("vert", "#2f4a3a"), ("green", "#2f4a3a"), ("kaki", "#5b5a3c"), ("sable", "#cbb98f"), ("beige", "#d9c9a8"),
    ("crème", "#efe4cc"), ("ivoire", "#efe6d2"), ("blanc", "#f2f0ea"), ("white", "#f2f0ea"), ("alabaster", "#efece4"),
    ("argent", "#c9c9c9"), ("silver", "#c9c9c9"), ("gris", "#7d7f82"), ("grey", "#7d7f82"), ("stealth", "#5f6368"),
    ("orange", "#e0782f"), ("jaune", "#e5a91e"), ("yellow", "#e5a91e"), ("violet", "#5b4a8b"), ("rouge", "#9b2f2f"),
    ("bordeaux", "#6b1f2a"), ("brun", "#6b4a32"), ("marron", "#6b4a32"), ("saumon", "#e3a68b"), ("positif", "#c8cbc4"),
]


def clean(t):
    return re.sub(r"\s+", " ", html.unescape(t or "")).strip()


def slug(t):
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:48]


def num(t):
    return float(t.replace(",", ".").replace(" ", "").replace(" ", ""))


def color_for(name):
    n = (name or "").lower()
    for word, c in COLOR_WORDS:
        if word in n:
            return c
    return "#9a978f"


def split_name(full):
    full = full.replace("‑", "-")
    main, _, ref = full.partition(" — ")
    brand = next((b for b in TWO_WORD_BRANDS if main.startswith(b)), None)
    if not brand:
        brand = main.split()[0]
        if brand == "G-Shock":           # « G-Shock GW-BX5600-1 » → Casio
            brand, main = "Casio", "Casio " + main
    model = main[len(brand):].strip()
    return brand, model, ref.strip()


def parse_dims(text):
    """« 46,7 × 43,2 × 12,7 mm • 52 g » / « 40 mm • 9,3 mm • 87 g » → diamètre, épaisseur, entre-cornes, poids."""
    out = {}
    if not text:
        return out
    w = re.search(r"(\d+(?:[,.]\d+)?)\s*g\b", text)
    if w:
        out["weight"] = num(w.group(1))
    head = text.split("•")[0] if "×" in text.split("•")[0] else text
    nums = [num(n) for n in re.findall(r"(\d+(?:[,.]\d+)?)(?=\s*(?:mm|×|$|\s))", head.replace(" g", " g "))]
    nums = [n for n in nums if 4 <= n <= 70 and n != out.get("weight")]
    thin = [n for n in nums if n < 20]
    big = [n for n in nums if n >= 25]
    if thin:
        out["thickness"] = min(thin)
    if len(big) >= 2:
        out["diameter"], out["lugToLug"] = min(big[:2]), max(big[:2])
    elif big:
        out["diameter"] = big[0]
    return out


def to_eur(price):
    """Valeur numérique approximative (en €) pour trier par prix."""
    p = price.replace(" ", " ")
    m = re.search(r"(\d[\d ]*(?:[,.]\d+)?)", p)
    if not m:
        return None
    v = num(m.group(1))
    if "USD" in p or "$" in p:
        v *= 0.92
    elif "£" in p:
        v *= 1.17
    return round(v)


def photo(img):
    """<img src data-fallbacks> → {"src": None, "remote": [urls…]}"""
    if img is None:
        return None
    urls = [img.get("src")] + json.loads(img.get("data-fallbacks") or "[]")
    urls = [u for u in urls if u]
    return {"src": None, "remote": urls}


def save_data_uri(uri, wid, name):
    m = re.match(r"data:image/(\w+);base64,(.+)", uri, re.S)
    path = OUT / "img" / wid / f"{name}.{m.group(1)}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(m.group(2)))
    return f"seed/img/{wid}/{path.name}"


def main(src):
    soup = BeautifulSoup(Path(src).read_text(encoding="utf-8"), "html.parser")

    # Tableau récapitulatif : style, statut, énergie, radio, prix
    recap = {}
    for tr in soup.select("tbody tr"):
        a = tr.select_one(".recap-model a")
        if not a:
            continue
        tds = [clean(td.get_text(" ")) for td in tr.find_all("td")]
        recap[int(a["href"].split("-")[1])] = {
            "style": tds[2], "status": tds[3], "availability": tds[4], "energy": tds[5],
            "radio": tds[6], "display": tds[7], "price": tds[8],
        }

    # Palettes de la carte de collection (montres choisies)
    palettes = {}
    for card in soup.select(".collection-card"):
        a = card.select_one(".pick a")
        if a:
            palettes[int(a["href"].split("-")[1])] = [
                {"name": g["title"], "color": re.search(r"#[0-9a-fA-F]{6}", g.select_one(".swatch")["style"]).group(0)}
                for g in card.select(".swatch-group")]

    watches, page_to_id = [], {}
    for sec in soup.select("section.spread"):
        page = int(sec["id"].split("-")[1])
        content = sec.select_one(".content-col")
        full = clean(content.h2.get_text())
        brand, model, ref = split_name(full)
        wid = slug(f"{brand} {model}")
        page_to_id[page] = wid

        specs = [[clean(s.select_one(".label").get_text()), clean(s.select_one(".value").get_text(" "))]
                 for s in content.select(".spec")]
        sp = {k: v for k, v in specs}
        dims = parse_dims(sp.get("Dimensions / poids") or sp.get("Dimensions") or "")
        if "diameter" not in dims:                                    # « Orient Bambino 38,4 mm »
            d = re.search(r"(\d+(?:,\d)?)\s*mm", full)
            if d:
                dims["diameter"] = num(d.group(1))
        text_all = " ".join(v for _, v in specs) + " " + content.get_text(" ")
        l2l = re.search(r"corne[- ]à[- ]corne[^0-9]{0,25}(\d+(?:[,.]\d+)?)\s*mm", text_all)
        l2l = l2l or re.search(r"(\d+(?:[,.]\d+)?)\s*mm\s*(?:de\s*)?corne[- ]à[- ]corne", text_all)
        if l2l and "lugToLug" not in dims:
            dims["lugToLug"] = num(l2l.group(1))
        straps = sp.get("Bracelets standards") or sp.get("Bracelets") or sp.get("Bracelet") or ""
        lug = re.search(r"(\d{2})\s*mm", straps)
        if lug and 12 <= int(lug.group(1)) <= 24:
            dims["lugWidth"] = int(lug.group(1))
        if "intégré" in (straps + sp.get("Style général", "")).lower():
            dims["integrated"] = True
        if "Poids" in sp and "weight" not in dims:
            w = re.search(r"(\d+(?:[,.]\d+)?)\s*g", sp["Poids"])
            if w:
                dims["weight"] = num(w.group(1))

        r = recap.get(page, {})
        movement = sp.get("Énergie") or sp.get("Énergie / mouvement") or sp.get("Mouvement") or r.get("energy", "")
        cal = re.search(r"calibre\s+([\w.\-]+)", movement, re.I)

        # Listes : pour / contre / lecture collection
        pros, cons, collection_note = [], [], ""
        for col in content.select(".column"):
            title = clean(col.h3.get_text()) if col.h3 else ""
            items = [clean(li.get_text(" ")) for li in col.select("li")]
            if "moins plaire" in title or "compromis" in title:
                cons = items
            elif "Lecture" in title:
                collection_note = " ".join(items) or clean(col.get_text(" ").replace(title, ""))
            else:
                pros = items
        opinion = content.select_one(".opinion-box p")
        links = [{"label": clean(a.get_text()).replace("↗", "").strip(), "url": a["href"]}
                 for a in content.select(".linkline a")]

        # Photos
        vis = sec.select_one(".visual-col")
        main_img = vis.select_one(".visual-frame img")
        night_img = vis.select_one(".night-box img")
        photos = {"main": photo(main_img), "night": photo(night_img)}
        if main_img is not None and main_img.get("src", "").startswith("data:"):
            photos["main"] = {"src": save_data_uri(main_img["src"], wid, "main"), "remote": []}
        if night_img is not None:
            cap = vis.select_one(".night-box .night-caption")
            photos["night"]["caption"] = clean(cap.get_text()) if cap else ""

        variants = []
        for vc in vis.select(".variant-card"):
            name = clean(vc.select_one(".variant-name").get_text()) if vc.select_one(".variant-name") else ""
            vref = clean(vc.select_one(".variant-ref").get_text()) if vc.select_one(".variant-ref") else ""
            link = vc.select_one(".variant-link")
            variants.append({
                "name": name or vref, "ref": vref, "color": color_for(name + " " + vref),
                "note": clean(vc.select_one(".variant-note").get_text()) if vc.select_one(".variant-note") else "",
                "url": link["href"] if link else "", "photo": photo(vc.select_one("img")),
            })
        if not variants and len(palettes.get(page, [])) > 1:      # coloris connus sans photo
            variants = [{"name": p["name"], "ref": "", "color": p["color"], "note": "", "url": "", "photo": None}
                        for p in palettes[page]]

        status = r.get("status", "")
        watches.append({
            "id": wid, "brand": brand, "model": model, "reference": ref,
            "categories": CATS_BY_PAGE.get(page, []),
            "status": "future" if "future" in status.lower() else "alternative",
            "eyebrow": clean(content.select_one(".eyebrow").get_text()) if content.select_one(".eyebrow") else "",
            "headline": clean(content.select_one(".subtitle").get_text()) if content.select_one(".subtitle") else "",
            "tagline": clean(content.select_one(".tagline").get_text()) if content.select_one(".tagline") else "",
            "summary": clean(content.select_one(".summary").get_text(" ")) if content.select_one(".summary") else "",
            "style": r.get("style") or sp.get("Style général", ""),
            "movement": r.get("energy") or movement,
            "movementDetail": movement,
            "caliber": cal.group(1) if cal else "",
            "radio": r.get("radio", ""),
            "display": r.get("display") or sp.get("Affichage", ""),
            "dims": dims,
            "crystal": sp.get("Verre", ""),
            "case": sp.get("Boîtier") or sp.get("Boîtier / bracelet", ""),
            "water": sp.get("Étanchéité", ""),
            "lume": sp.get("Éclairage / lume") or sp.get("Lume", ""),
            "price": r.get("price") or sp.get("Prix indicatif", ""),
            "priceEur": to_eur(r.get("price") or sp.get("Prix indicatif", "")),
            "availability": r.get("availability") or sp.get("Disponibilité", ""),
            "specs": specs,
            "pros": pros, "cons": cons, "collectionNote": collection_note,
            "reviews": clean(opinion.get_text(" ")) if opinion else "",
            "links": links,
            "photos": photos,
            "variants": variants, "favoriteVariant": 0,
            "notes": "",
            "source": f"v27 · page {page}",
        })

    # Pièces citées sans page complète dans la v27
    extra_cats = {"Knot AT-38 Urushi": ["dress", "art"], "Citizen NB1060 Silver Leaf": ["dress", "art"],
                  "MAEN Manhattan 39 Ultra-Thin": ["sport", "dress"]}
    for card in soup.select(".alt-card"):
        full = clean(card.h4.get_text())
        brand, model, ref = split_name(full)
        desc = clean(card.p.get_text())
        mms = [num(n) for n in re.findall(r"(\d+(?:,\d+)?)\s*mm", desc)]
        dims = {"diameter": mms[0]} if mms else {}
        if len(mms) > 1 and mms[1] < 20:
            dims["thickness"] = mms[1]
        a = card.a
        watches.append({
            "id": slug(f"{brand} {model}"), "brand": brand, "model": model, "reference": ref,
            "categories": extra_cats.get(full, ["dress"]), "status": "alternative",
            "eyebrow": "", "headline": "", "tagline": "", "summary": desc, "style": "", "movement": "",
            "movementDetail": "", "caliber": "", "radio": "", "display": "", "dims": dims, "crystal": "",
            "case": "", "water": "", "lume": "", "price": "", "priceEur": None, "availability": "",
            "specs": [], "pros": [], "cons": [], "collectionNote": "", "reviews": "",
            "links": [{"label": clean(a.get_text()).replace("↗", "").strip(), "url": a["href"]}] if a else [],
            "photos": {"main": None, "night": None}, "variants": [], "favoriteVariant": 0, "notes": "",
            "source": "v27 · carte de collection",
        })

    # Photos déjà détourées pour la maquette
    for wid, f in {"charlie-paris-concordia": "concordia.png", "citizen-tsuyosa-yellow": "tsuyosa.png"}.items():
        w = next((w for w in watches if w["id"] == wid), None)
        src = ROOT / "mockups" / "img" / f
        if w and src.exists():
            for old in (OUT / "img" / wid).glob("main.*"):
                old.unlink()
            dst = OUT / "img" / wid / "main.png"
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(src.read_bytes())
            w["photos"]["main"] = {"src": f"seed/img/{wid}/main.png", "remote": (w["photos"]["main"] or {}).get("remote", [])}

    cats = [dict(c, pick=page_to_id.get(PICKS.get(c["id"]))) for c in CATEGORIES]
    data = {"version": 1, "wrist": {"circumference": 18}, "profile": PROFILE,
            "categories": cats, "watches": watches}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "watches.json").write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(watches)} montres → {OUT / 'watches.json'}")


if __name__ == "__main__":
    main(sys.argv[1])
