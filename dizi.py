import requests
from bs4 import BeautifulSoup
import json
import time
import html
from urllib.parse import urljoin

BASE_URL = "https://www.dizipal1226.com/diziler"
OUT_JSON = "series.json"
OUT_HTML = "index.html"
MAX_SERIES = 1

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# Dizipal Kaynak Kodundan Alınan Sabit Kategoriler
FIXED_GENRES = [
    "Aile", "Aksiyon", "Animasyon", "Anime", "Belgesel", "Bilimkurgu",
    "Biyografi", "Dram", "Editörün Seçtikleri", "Erotik", "Fantastik",
    "Gerilim", "Gizem", "Komedi", "Korku", "Macera", "Mubi", "Müzik",
    "Romantik", "Savaş", "Spor", "Suç", "Tarih", "Western", "Yerli",
    "Netflix", "Exxen", "BluTV", "Disney+", "Amazon", "TOD", "Gain"
]

# ---------------- GENEL ----------------

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

# ---------------- DİZİ LİSTESİ ----------------

def get_all_series_cards():
    soup = get_soup(BASE_URL)
    if not soup:
        return []

    series = []
    seen = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/dizi/") and href.count("/") == 2:
            full = urljoin(BASE_URL, href)
            if full in seen:
                continue
            seen.add(full)

            img = a.find("img")
            image = ""
            if img:
                image = img.get("data-src") or img.get("src") or ""
                if image.startswith("//"):
                    image = "https:" + image

            series.append({
                "url": full,
                "image": image
            })

            if len(series) >= MAX_SERIES:
                break

    return series

# ---------------- DİZİ SAYFASI ----------------

def parse_series(card):
    soup = get_soup(card["url"])
    if not soup:
        return None

    h = soup.find("h5")
    title = html.unescape(h.get_text(" ", strip=True)) if h else ""

    p = soup.find("p")
    summary = html.unescape(p.get_text(" ", strip=True)) if p else ""

    # 🔹 TÜRLER (FIXED_GENRES’E GÖRE – KOMEDİ YERLİ vb.)
    genres = []
    for key in soup.find_all("div", class_="key"):
        if key.get_text(strip=True) == "Türler":
            value = key.find_next_sibling("div", class_="value")
            if value:
                raw_text = html.unescape(value.get_text(" ", strip=True))
                for g in FIXED_GENRES:
                    if g in raw_text:
                        genres.append(g)
            break

    data = {
        "title": title,
        "image": card["image"],
        "summary": summary,
        "genres": genres,
        "seasons": {}
    }

    seen_eps = set()

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/sezon-" in href and "/bolum-" in href:
            ep_url = urljoin(card["url"], href)
            if ep_url in seen_eps:
                continue
            seen_eps.add(ep_url)

            season = href.split("/sezon-")[1].split("/")[0]
            episode = href.split("/bolum-")[1]

            video = get_iframe(ep_url)
            time.sleep(0.15)

            data["seasons"].setdefault(season, [])
            data["seasons"][season].append({
                "episode": f"{episode}. Bölüm",
                "videoUrl": video
            })

    return data


# ---------------- HTML ----------------

def create_html(series_list):
    data_json = json.dumps(series_list, ensure_ascii=False)

    html_out = f"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<title>Dizipal Arşiv</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body {{
    margin:0;
    font-family:-apple-system, sans-serif;
    background:#344966;
    color:#fff;
}}
.header {{
    padding:15px;
    background:#2c3e50;
    position:sticky;
    top:0;
}}
.grid {{
    display:grid;
    grid-template-columns:repeat(auto-fill, minmax(140px,1fr));
    gap:15px;
    padding:20px;
}}
.card {{
    background:#496785;
    border-radius:10px;
    overflow:hidden;
    cursor:pointer;
}}
.card img {{
    width:100%;
    aspect-ratio:2/3;
    object-fit:cover;
}}
.card-title {{
    padding:8px;
    font-size:.85em;
    text-align:center;
    font-weight:bold;
}}
#detail {{
    display:none;
    padding:20px;
}}
.back {{
    cursor:pointer;
    color:#f39c12;
    margin-bottom:15px;
    display:inline-block;
}}
.genre {{
    background:#e67e22;
    display:inline-block;
    padding:5px 10px;
    border-radius:15px;
    margin:0 5px 10px 0;
    font-size:.8em;
}}
.season {{
    margin-top:20px;
}}
.episode {{
    background:#496785;
    padding:10px;
    border-radius:8px;
    margin:5px 0;
}}
.episode a {{
    color:#f39c12;
    text-decoration:none;
    font-weight:bold;
}}
</style>
</head>
<body>

<div class="header"><h2>Dizi Arşivi</h2></div>
<div id="list" class="grid"></div>

<div id="detail">
    <span class="back" onclick="goBack()">← Geri</span>
    <h1 id="dTitle"></h1>
    <div id="dGenres"></div>
    <p id="dSummary"></p>
    <div id="seasons"></div>
</div>

<script>
const data = {data_json};
const list = document.getElementById("list");
const detail = document.getElementById("detail");

function renderList() {{
    list.innerHTML = "";
    detail.style.display = "none";
    list.style.display = "grid";

    data.forEach(d => {{
        const c = document.createElement("div");
        c.className = "card";
        c.innerHTML = `
            <img src="${{d.image}}" onerror="this.src='https://via.placeholder.com/200x300?text=No+Image'">
            <div class="card-title">${{d.title}}</div>
        `;
        c.onclick = () => openDetail(d);
        list.appendChild(c);
    }});
}}

function openDetail(d) {{
    list.style.display = "none";
    detail.style.display = "block";

    document.getElementById("dTitle").innerText = d.title;
    document.getElementById("dSummary").innerText = d.summary || "Özet bulunamadı";

    const g = document.getElementById("dGenres");
    g.innerHTML = "";
    if (d.genres && d.genres.length) {{
        d.genres.forEach(x => {{
            const s = document.createElement("span");
            s.className = "genre";
            s.innerText = x;
            g.appendChild(s);
        }});
    }}

    const s = document.getElementById("seasons");
    s.innerHTML = "";

    Object.keys(d.seasons).sort().forEach(season => {{
        const div = document.createElement("div");
        div.className = "season";
        div.innerHTML = `<h2>Sezon ${{season}}</h2>`;

        d.seasons[season].forEach(ep => {{
            const e = document.createElement("div");
            e.className = "episode";
            e.innerHTML = `<a href="${{ep.videoUrl || ep.url}}" target="_blank">${{ep.episode}}</a>`;
            div.appendChild(e);
        }});

        s.appendChild(div);
    }});
}}

function goBack() {{
    renderList();
}}

renderList();
</script>
</body>
</html>"""

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(html_out)

# ---------------- MAIN ----------------

def main():
    cards = get_all_series_cards()
    all_series = []

    for card in cards:
        s = parse_series(card)
        if s:
            all_series.append(s)

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_series, f, ensure_ascii=False, indent=2)

    create_html(all_series)
    print("✅ Dizi + Tür + Sezon/Bölüm tamamlandı")

if __name__ == "__main__":
    main()
