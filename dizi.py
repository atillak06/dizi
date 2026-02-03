import requests
from bs4 import BeautifulSoup
import json
import time
import html
from urllib.parse import urljoin, urlparse, parse_qs

BASE_URL = "https://dizipal.uk/diziler/"
OUT_JSON = "series.json"
OUT_HTML = "index.html"
MAX_SERIES = 30

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

FIXED_GENRES = [
    "Aile", "Aksiyon", "Animasyon", "Anime", "Belgesel", "Bilimkurgu",
    "Biyografi", "Dram", "Fantastik", "Gerilim", "Gizem", "Komedi",
    "Korku", "Macera", "Romantik", "Savaş", "Suç", "Tarih", "Yerli"
]

# ------------------------------------------------

def get_soup(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except:
        return None

def get_iframe(url):
    soup = get_soup(url)
    if not soup:
        return ""
    iframe = soup.find("iframe")
    return iframe["src"] if iframe and iframe.get("src") else ""

# ------------------------------------------------
# DİZİ LİSTESİ
# ------------------------------------------------

def get_all_series_cards():
    soup = get_soup(BASE_URL)
    if not soup:
        return []

    series = []
    seen = set()

    for item in soup.select("div.post-item"):
        a = item.find("a", href=True)
        if not a:
            continue

        url = a["href"]
        if url in seen:
            continue
        seen.add(url)

        img = item.find("img")
        image = img.get("data-src") or img.get("src") if img else ""

        series.append({
            "url": url,
            "image": image
        })

        if len(series) >= 99999999:
            print("Güvenlik limiti.")
            break

    return series

# ------------------------------------------------
# DİZİ DETAY + SEZON + BÖLÜM
# ------------------------------------------------

def parse_series(card):
    soup = get_soup(card["url"])
    if not soup:
        return None

    title_tag = soup.find("h1")
    title = html.unescape(title_tag.get_text(strip=True)) if title_tag else ""

    summary_tag = soup.find("p")
    summary = html.unescape(summary_tag.get_text(strip=True)) if summary_tag else ""

    genres = []
    for g in FIXED_GENRES:
        if g.lower() in soup.get_text().lower():
            genres.append(g)

    data = {
        "title": title,
        "image": card["image"],
        "summary": summary,
        "genres": genres,
        "seasons": {}
    }

    # 🔹 SEZON LİNKLERİ (SET ZATEN OK)
    season_links = set()
    for a in soup.select("#season-options-list a"):
        href = a.get("href")
        if href:
            season_links.add(urljoin(card["url"], href))

    if not season_links:
        season_links.add(card["url"])

    # 🔥 KRİTİK: TEKİL BÖLÜM KONTROLÜ
    seen_episodes = set()

    for season_url in season_links:
        qs = parse_qs(urlparse(season_url).query)
        season_no = qs.get("sezon", ["1"])[0]

        season_soup = get_soup(season_url)
        if not season_soup:
            continue

        for ep in season_soup.select("div.episode-item a[href]"):
            ep_url = ep["href"]

            # 🚫 DAHA ÖNCE EKLENDİYSE ATLANSIN
            if ep_url in seen_episodes:
                continue
            seen_episodes.add(ep_url)

            ep_title = ep.get("title", "")
            if "Bölüm" in ep_title:
                episode_no = ep_title.split("Bölüm")[0].split()[-1]
            else:
                episode_no = ep.get_text(strip=True)

            video = get_iframe(ep_url)
            time.sleep(0.2)

            data["seasons"].setdefault(season_no, [])
            data["seasons"][season_no].append({
                "episode": f"{episode_no}. Bölüm",
                "videoUrl": video
            })

    return data


# ------------------------------------------------
# HTML OLUŞTURMA (AYNI – DEĞİŞMEDİ)
# ------------------------------------------------

def generate_html(series_list):
    cards = ""

    for s in series_list:
        seasons_html = ""

        for season_no, episodes in s.get("seasons", {}).items():
            ep_html = ""
            for ep in episodes:
                ep_html += f"""
                <li>
                    <a href="{ep['videoUrl']}" target="_blank">
                        ▶ {ep['episode']}
                    </a>
                </li>
                """

            seasons_html += f"""
            <details class="season">
                <summary>📺 Sezon {season_no}</summary>
                <ul>
                    {ep_html}
                </ul>
            </details>
            """

        cards += f"""
        <div class="card">
            <img src="{s['image']}" alt="{s['title']}">
            <h3>{s['title']}</h3>
            <p class="summary">{s.get('summary','')}</p>
            {seasons_html}
        </div>
        """

    return f"""
<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Dizi Arşivi</title>
<style>
body {{
    background:#0f0f0f;
    color:#fff;
    font-family:Arial;
}}
.grid {{
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(200px,1fr));
    gap:15px;
}}
.card {{
    background:#1a1a1a;
    padding:10px;
    border-radius:8px;
}}
.card img {{
    width:100%;
    border-radius:6px;
}}
.card h3 {{
    margin:8px 0 4px;
}}
.summary {{
    font-size:13px;
    color:#ccc;
}}
.season {{
    margin-top:8px;
}}
.season summary {{
    cursor:pointer;
    font-weight:bold;
    color:#0f0;
}}
.season ul {{
    list-style:none;
    padding-left:10px;
}}
.season li a {{
    display:block;
    padding:4px 0;
    color:#0ff;
    text-decoration:none;
    font-size:14px;
}}
.season li a:hover {{
    text-decoration:underline;
}}
</style>
</head>
<body>

<h1>📺 Dizi Listesi ({len(series_list)})</h1>
<div class="grid">
{cards}
</div>

</body>
</html>
"""


# ------------------------------------------------
# MAIN
# ------------------------------------------------

def main():
    cards = get_all_series_cards()
    all_series = []

    for card in cards:
        print("🔍", card["url"])
        s = parse_series(card)
        if s:
            all_series.append(s)

    # JSON
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_series, f, ensure_ascii=False, indent=2)

    # HTML
    html_content = generate_html(all_series)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_content)

    print("✅ Dizi + Sezon + Bölüm + Iframe + HTML tamamlandı")


if __name__ == "__main__":
    main()
