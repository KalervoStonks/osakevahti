"""Ilmaiset tietolähteet: Google News, Yahoo Finance RSS, StockTwits, Reddit."""
import hashlib

import feedparser
import requests

UA = {"User-Agent": "Mozilla/5.0 (Osakevahti; henkilokohtainen uutisseuranta)"}


def _id(*osat: str) -> str:
    return hashlib.sha1("|".join(osat).encode("utf-8")).hexdigest()[:16]


def google_news(ticker: str, nimi: str) -> list[dict]:
    haku = requests.utils.quote(f'"{nimi}" OR "{ticker}" when:2d')
    url = f"https://news.google.com/rss/search?q={haku}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    tulokset = []
    for e in feed.entries[:12]:
        linkki = e.get("link", "")
        otsikko = e.get("title", "")
        if not otsikko:
            continue
        tulokset.append({
            "id": _id("gnews", linkki or otsikko),
            "ticker": ticker,
            "tyyppi": "uutinen",
            "lahde": "Google News",
            "otsikko": otsikko,
            "url": linkki,
            "julkaistu": e.get("published", ""),
        })
    return tulokset


def yahoo_rss(ticker: str) -> list[dict]:
    url = (
        "https://feeds.finance.yahoo.com/rss/2.0/headline"
        f"?s={ticker}&region=US&lang=en-US"
    )
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    tulokset = []
    for e in feed.entries[:10]:
        otsikko = e.get("title", "")
        if not otsikko:
            continue
        tulokset.append({
            "id": _id("yahoo", e.get("link", otsikko)),
            "ticker": ticker,
            "tyyppi": "uutinen",
            "lahde": "Yahoo Finance",
            "otsikko": otsikko,
            "url": e.get("link", ""),
            "julkaistu": e.get("published", ""),
        })
    return tulokset


def stocktwits(symboli: str) -> list[dict]:
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{symboli}.json"
    try:
        r = requests.get(url, headers=UA, timeout=20)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []
    viestit = []
    for m in data.get("messages", [])[:30]:
        teksti = (m.get("body") or "").strip()
        if not teksti:
            continue
        viestit.append({
            "id": _id("st", str(m.get("id", teksti))),
            "lahde": "StockTwits",
            "teksti": teksti[:500],
            "aika": m.get("created_at", ""),
        })
    return viestit


def reddit(ticker: str, nimi: str) -> list[dict]:
    haku = requests.utils.quote(f'"{nimi}" OR "{ticker}"')
    url = f"https://www.reddit.com/search.json?q={haku}&sort=new&t=day&limit=15"
    try:
        r = requests.get(url, headers=UA, timeout=20)
        if r.status_code != 200:
            return []
        data = r.json()
    except Exception:
        return []
    viestit = []
    for lapsi in data.get("data", {}).get("children", []):
        d = lapsi.get("data", {})
        teksti = " — ".join(x for x in [d.get("title", ""), (d.get("selftext") or "")[:400]] if x).strip()
        if not teksti:
            continue
        viestit.append({
            "id": _id("rd", d.get("id", teksti)),
            "lahde": "Reddit",
            "teksti": teksti[:500],
            "aika": str(d.get("created_utc", "")),
        })
    return viestit
