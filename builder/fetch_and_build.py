# ============================================================
# KI-Ticker Build Script – Abschnitt A
# Imports, Setup, Konstanten
# ============================================================

import os
import re
import time
import json
import yaml
import hashlib
import datetime
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup
from slugify import slugify
from jinja2 import Environment, FileSystemLoader, select_autoescape


# ------------------------------------------------------------
# Verzeichnisse & Basis-Pfade
# ------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
OUTPUT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "public"))

# sicherstellen dass das Ausgabe-Verzeichnis existiert
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(os.path.join(OUTPUT_DIR, "assets"), exist_ok=True)


# ------------------------------------------------------------
# Pagination Einstellungen
# ------------------------------------------------------------
ITEMS_PER_PAGE = 30  # Anzahl Artikel pro Seite


# ------------------------------------------------------------
# Site Meta / SEO Defaults
# ------------------------------------------------------------
SITE_META = {
    "title": "KI‑Ticker – Aktuelle KI‑News",
    "description": "Automatisierte Nachrichtenübersicht zu KI, Machine Learning, LLMs und Forschung.",
    "url": "https://ki-ticker.boehmonline.space",
    "image": "https://ki-ticker.boehmonline.space/assets/og.png"
}

ADSENSE = {
    "enabled": True,
    "publisher_id": "pub-2616688648278798"  # <-- deine ID
}
# ============================================================
# KI-Ticker Build Script – Abschnitt B
# Feed-Loading, HTML-Cleaning, Text-Extraktion
# ============================================================


# ------------------------------------------------------------
# Feeds laden
# ------------------------------------------------------------
def load_feed_sources():
    path = os.path.join(BASE_DIR, "feeds.yaml")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data["sources"]


# ------------------------------------------------------------
# HTML aus Feed-Descriptions entfernen
# ------------------------------------------------------------
def clean_html(text, max_length=280):
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    short = soup.get_text(" ", strip=True)

    if len(short) > max_length:
        return short[:max_length].rstrip() + "…"
    return short


# ------------------------------------------------------------
# Hash-ID für artikelgenerierung
# ------------------------------------------------------------
def make_hash_id(*parts):
    h = hashlib.sha256()
    for p in parts:
        if p:
            h.update(str(p).encode("utf-8"))
    return h.hexdigest()[:16]
# ============================================================
# KI-Ticker Build Script – Abschnitt C
# Normalisierung & Strukturierung der Feed-Einträge
# ============================================================


# ------------------------------------------------------------
# Veröffentlichungsdatum aus Feed-Eintrag ziehen
# ------------------------------------------------------------
def extract_datetime(entry):
    """
    Versucht die beste verfügbare Zeitinfo zu bekommen.
    Falls kein Datum vorhanden ist, wird NOW UTC genutzt.
    """
    dt_parsed = (
        entry.get("published_parsed")
        or entry.get("updated_parsed")
        or None
    )

    if dt_parsed:
        return datetime.datetime.fromtimestamp(
            time.mktime(dt_parsed),
            tz=datetime.timezone.utc
        )

    # fallback
    return datetime.datetime.now(datetime.timezone.utc)


# ------------------------------------------------------------
# Bild aus RSS-Feed auslesen (falls verfügbar)
# ------------------------------------------------------------
def extract_image(entry):
    """
    Versucht ein Bild aus media:content, enclosure oder og:image herauszuziehen.
    """
    # media:content
    media = entry.get("media_content") or []
    if media and isinstance(media, list):
        url = media[0].get("url")
        if url:
            return url

    # enclosure
    if "links" in entry:
        for link in entry["links"]:
            if link.get("rel") == "enclosure" and "image" in link.get("type", ""):
                return link.get("href")

    # nichts gefunden
    return None


# ------------------------------------------------------------
# Feed-Eintrag in unser internes Format bringen
# ------------------------------------------------------------
def normalize_item(entry, source_name):
    title = (entry.get("title") or "").strip()
    link = (entry.get("link") or "").strip()
    summary = clean_html(
        entry.get("summary")
        or entry.get("description")
        or ""
    )

    published_dt = extract_datetime(entry)
    image_url = extract_image(entry)

    return {
        "id": make_hash_id(source_name, title, link),
        "title": title or "(ohne Titel)",
        "url": link,
        "summary": summary,
        "source": source_name,
        "published": published_dt,
        "published_iso": published_dt.isoformat(),
        "domain": urlparse(link).netloc.replace("www.", ""),
        "image": image_url,
        "slug": slugify(title)[:80] if title else make_hash_id(link)
    }
# ============================================================
# KI-Ticker Build Script – Abschnitt D
# Feeds abrufen, Fehlerbehandlung, Deduplikation
# ============================================================


# ------------------------------------------------------------
# Einzelnen RSS-Feed abrufen
# ------------------------------------------------------------
def fetch_single_feed(source):
    name = source["name"]
    url = source["url"]

    print(f"[INFO] Lade Feed: {name} ({url})")

    try:
        feed = feedparser.parse(url)

        if feed.bozo:
            # bozo: True → Fehler beim Parsen
            print(f"[WARN] Feed '{name}' konnte nicht sauber gelesen werden: {feed.bozo_exception}")

        entries = feed.entries[:40]  # Hardcap pro Feed
        normalized = [normalize_item(e, name) for e in entries]

        return normalized

    except Exception as ex:
        print(f"[ERROR] Fehler beim Laden von {name}: {ex}")
        return []


# ------------------------------------------------------------
# Alle Feeds abrufen
# ------------------------------------------------------------
def fetch_all_feeds():
    sources = load_feed_sources()
    all_items = []

    for src in sources:
        items = fetch_single_feed(src)
        all_items.extend(items)

    return all_items


# ------------------------------------------------------------
# Deduplikation + Sortierung
# ------------------------------------------------------------
def dedupe_and_sort(items, max_items=300):
    """
    Entfernt doppelte Artikel:
    - duplikate basierend auf (Titel, Domain)
    Sortiert nach Veröffentlichungszeit (neu → alt)
    """
    seen = set()
    result = []

    for item in sorted(items, key=lambda x: x["published"], reverse=True):
        key = (item["title"].lower().strip(), item["domain"])

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

        if len(result) >= max_items:
            break

    return result
# ============================================================
# KI-Ticker Build Script – Abschnitt E
# Pagination-System
# ============================================================


def paginate_items(items, per_page=ITEMS_PER_PAGE):
    """
    Teilt die Artikel in mehrere Seiten auf.
    page 1 = index.html
    page N = /page/N/index.html
    """
    pages = []
    total = len(items)
    page_count = (total + per_page - 1) // per_page

    for page_number in range(1, page_count + 1):
        start = (page_number - 1) * per_page
        end = start + per_page
        sub_items = items[start:end]

        # URL Logik
        if page_number == 1:
            url = SITE_META["url"]
        else:
            url = f'{SITE_META["url"]}/page/{page_number}/'

        pages.append({
            "number": page_number,
            "items": sub_items,
            "url": url,
            "generator": f"KI-Ticker Page {page_number}",
        })

    return pages


def build_pagination_metadata(current_page, total_pages):
    """
    Stellt prev/next-Links für Template bereit.
    """
    base = "/page"

    pagination = {
        "current_page": current_page,
        "page_url": f"{SITE_META['url']}/page/{current_page}/" if current_page > 1 else SITE_META["url"],
        "prev": None,
        "next": None
    }

    # Prev (neuere Artikel)
    if current_page > 2:
        pagination["prev"] = f"/page/{current_page - 1}/"
    elif current_page == 2:
        pagination["prev"] = "/"

    # Next (ältere Artikel)
    if current_page < total_pages:
        pagination["next"] = f"/page/{current_page + 1}/"

    return pagination
# ============================================================
# KI-Ticker Build Script – Abschnitt F‑1
# Template-Engine & generische Renderer-Funktionen
# ============================================================

# ------------------------------------------------------------
# Template Environment initialisieren
# ------------------------------------------------------------
env = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(['html', 'xml'])
)


# ------------------------------------------------------------
# Hilfsfunktion: Datei ins public/ Verzeichnis schreiben
# ------------------------------------------------------------
def write_file(path, content):
    """
    Schreibt Textdateien nach public/.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


# ------------------------------------------------------------
# Hilfsfunktion: Template rendern
# ------------------------------------------------------------
def render_template(template_name, **kwargs):
    """
    Rendert ein Jinja2-Template mit übergebenen Variablen.
    """
    tpl = env.get_template(template_name)
    return tpl.render(**kwargs)


# ------------------------------------------------------------
# Hilfsfunktion: Verzeichnisse sicher anlegen
# ------------------------------------------------------------
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)
# ============================================================
# KI-Ticker Build Script – Abschnitt F‑2
# Rendering der Startseite (index.html)
# ============================================================

def render_index_page(items):
    """
    Baut die index.html auf Basis der neuesten Artikel.
    Items = bereits sortiertes und dedupliziertes Array.
    """

    now = datetime.datetime.now(datetime.timezone.utc)

    # Startseite ist IMMER Seite 1
    pagination = {
        "current_page": 1,
        "page_url": SITE_META["url"],
        "prev": None,
        "next": None
    }

    html = render_template(
        "index.html.j2",
        items=items[:ITEMS_PER_PAGE],
        site=SITE_META,
        adsense=ADSENSE,
        pagination=pagination,
        last_updated=now.strftime("%d.%m.%Y %H:%M UTC"),
        now=now
    )

    # index.html schreiben
    out_path = os.path.join(OUTPUT_DIR, "index.html")
    write_file(out_path, html)

    print("[OK] index.html erzeugt")
# ============================================================
# KI-Ticker Build Script – Abschnitt F‑3
# Rendering der Pagination-Seiten (/page/X/index.html)
# ============================================================

def render_pagination_pages(pages):
    """
    Rendert alle Pagination-Seiten auf Basis der paginierten Items.
    Jede Seite wird als /page/<n>/index.html ausgegeben.
    """
    total_pages = len(pages)
    now = datetime.datetime.now(datetime.timezone.utc)

    for page in pages:
        page_number = page["number"]
        items = page["items"]

        # Pagination-Metadaten vorbereiten
        pagination_data = build_pagination_metadata(
            current_page=page_number,
            total_pages=total_pages
        )

        html = render_template(
            "page.html.j2",
            items=items,
            site=SITE_META,
            adsense=ADSENSE,
            pagination=pagination_data,
            last_updated=now.strftime("%d.%m.%Y %H:%M UTC"),
            now=now
        )

        # Pfad erzeugen
        if page_number == 1:
            # Wird bereits durch render_index_page erstellt
            out_path = os.path.join(OUTPUT_DIR, "index.html")
        else:
            out_dir = os.path.join(OUTPUT_DIR, "page", str(page_number))
            ensure_dir(out_dir)
            out_path = os.path.join(out_dir, "index.html")

        write_file(out_path, html)

        print(f"[OK] Seite {page_number} erzeugt → {out_path}")
# ============================================================
# KI-Ticker Build Script – Abschnitt F‑4
# Rendering der statischen Seiten
# ============================================================

def render_static_pages():
    """
    Rendert alle statischen Seiten wie Impressum, Datenschutz, About, Sources.
    """

    now = datetime.datetime.now(datetime.timezone.utc)

    static_pages = [
        ("about.html.j2", "about.html"),
        ("impressum.html.j2", "impressum.html"),
        ("datenschutz.html.j2", "datenschutz.html"),
        ("sources.html.j2", "sources.html"),
    ]

    for tpl_name, output_name in static_pages:
        html = render_template(
            tpl_name,
            site=SITE_META,
            adsense=ADSENSE,
            last_updated=now.strftime("%d.%m.%Y %H:%M UTC"),
            now=now
        )

        out_path = os.path.join(OUTPUT_DIR, output_name)
        write_file(out_path, html)

        print(f"[OK] Statische Seite erzeugt → {output_name}")
# ============================================================
# KI-Ticker Build Script – Abschnitt F‑5
# Metadateien: sitemap.xml, feed.xml, robots, ads.txt, CNAME
# ============================================================


# ------------------------------------------------------------
# Sitemap generieren
# ------------------------------------------------------------
def build_sitemap(pages):
    """
    Erstellt eine einfache sitemap.xml für Google.
    Enthält Startseite + alle Pagination-Seiten.
    """

    urls = [SITE_META["url"]]

    for page in pages:
        if page["number"] == 1:
            continue
        urls.append(f'{SITE_META["url"]}/page/{page["number"]}/')

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'

    for url in urls:
        xml += f'  <url><loc>{url}</loc></url>\n'

    xml += '</urlset>'

    write_file(os.path.join(OUTPUT_DIR, "sitemap.xml"), xml)
    print("[OK] sitemap.xml erzeugt")


# ------------------------------------------------------------
# Eigenen RSS-Feed generieren
# ------------------------------------------------------------
def build_rss_feed(all_items):
    """
    Erstellt einen eigenen RSS-Feed des KI-Tickers,
    damit andere dich abonnieren können.
    """

    rss_items = all_items[:50]  # Limit: neuesten 50

    now = datetime.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
  <title>KI‑Ticker – Automatisierte KI‑News</title>
  <description>Die neuesten Meldungen aus der Welt der Künstlichen Intelligenz.</description>
  <link>{SITE_META["url"]}</link>
  <lastBuildDate>{now}</lastBuildDate>
  <language>de</language>
"""

    for item in rss_items:
        rss += f"""
  <item>
    <title><![CDATA[{item['title']}]]></title>
    <description><![CDATA[{item['summary']}]]></description>
    <link>{item['url']}</link>
    <pubDate>{item['published'].strftime("%a, %d %b %Y %H:%M:%S GMT")}</pubDate>
    <guid isPermaLink="false">{item['id']}</guid>
  </item>
"""

    rss += """
</channel>
</rss>
"""

    write_file(os.path.join(OUTPUT_DIR, "feed.xml"), rss)
    print("[OK] RSS-Feed feed.xml erzeugt")


# ------------------------------------------------------------
# robots.txt erzeugen
# ------------------------------------------------------------
def build_robots():
    robots = f"""User-agent: *
Allow: /
Sitemap: {SITE_META["url"]}/sitemap.xml
"""
    write_file(os.path.join(OUTPUT_DIR, "robots.txt"), robots)
    print("[OK] robots.txt erzeugt")


# ------------------------------------------------------------
# ads.txt erzeugen (für AdSense)
# ------------------------------------------------------------
def build_ads():
    ads = f"google.com, {ADSENSE['publisher_id']}, DIRECT, f08c47fec0942fa0\n"
    write_file(os.path.join(OUTPUT_DIR, "ads.txt"), ads)
    print("[OK] ads.txt erzeugt")


# ------------------------------------------------------------
# CNAME erzeugen (für GitHub Pages)
# ------------------------------------------------------------
def build_cname():
    write_file(os.path.join(OUTPUT_DIR, "CNAME"), "ki-ticker.boehmonline.space\n")
    print("[OK] CNAME erzeugt")


# ------------------------------------------------------------
# OG Placeholder einrichten (optional)
# ------------------------------------------------------------
def ensure_og_placeholder():
    """
    Falls du assets/og.png noch nicht selbst hochgeladen hast,
    erstellen wir eine leere Placeholder-Datei.
    """
    og_path = os.path.join(OUTPUT_DIR, "assets", "og.png")
    if not os.path.exists(og_path):
        with open(og_path, "wb") as f:
            f.write(b"")  # leerer Platzhalter
        print("[INFO] OG Platzhalter erzeugt (assets/og.png)")
# ============================================================
# KI-Ticker Build Script – Abschnitt G
# Main-Funktion & gesamte Build-Pipeline
# ============================================================

def build_all():
    print("============================================================")
    print("  KI‑Ticker Build gestartet")
    print("============================================================")

    # --------------------------------------------------------
    # 1. Feeds abrufen
    # --------------------------------------------------------
    all_items = fetch_all_feeds()
    print(f"[INFO] Roh-Artikel geladen: {len(all_items)}")

    # --------------------------------------------------------
    # 2. Deduplikation + Sortierung
    # --------------------------------------------------------
    clean_items = dedupe_and_sort(all_items)
    print(f"[INFO] Nach Deduplikation: {len(clean_items)} Artikel")

    # --------------------------------------------------------
    # 3. Pagination vorbereiten
    # --------------------------------------------------------
    pages = paginate_items(clean_items, per_page=ITEMS_PER_PAGE)
    print(f"[INFO] Generierte Seiten: {len(pages)}")

    # --------------------------------------------------------
    # 4. Startseite + Pagination-Seiten rendern
    # --------------------------------------------------------
    render_index_page(clean_items)
    render_pagination_pages(pages)

    # --------------------------------------------------------
    # 5. Statische Seiten (Impressum, Datenschutz, About, Sources)
    # --------------------------------------------------------
    render_static_pages()

    # --------------------------------------------------------
    # 6. Metadateien generieren
    # --------------------------------------------------------
    build_sitemap(pages)
    build_rss_feed(clean_items)
    build_robots()
    build_ads()
    build_cname()
    ensure_og_placeholder()

    print("============================================================")
    print("  KI‑Ticker Build erfolgreich abgeschlossen!")
    print("============================================================")


# ------------------------------------------------------------
# Skript aufrufen
# ------------------------------------------------------------
if __name__ == "__main__":
    build_all()
