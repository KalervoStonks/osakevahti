"""Ilmaiset tietolähteet: uutiset, some, viralliset tiedotteet, kurssit, tuloskalenteri."""
import hashlib
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from . import config

UA = {"User-Agent": "Mozilla/5.0 (Osakevahti; henkilokohtainen uutisseuranta; contact: osakevahti@example.com)"}
SEC_UA = {"User-Agent": "Osakevahti henkilokohtainen tutkimus osakevahti@example.com"}


def _id(*osat: str) -> str:
    return hashlib.sha1("|".join(osat).encode("utf-8")).hexdigest()[:16]


# --- Uutiset -----------------------------------------------------------------

def google_news(ticker: str, nimi: str) -> list[dict]:
    haku = requests.utils.quote(f'"{nimi}" OR "{ticker}" when:2d')
    url = f"https://news.google.com/rss/search?q={haku}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    tulokset = []
    for e in feed.entries[:12]:
        otsikko = e.get("title", "")
        if not otsikko:
            continue
        tulokset.append({
            "id": _id("gnews", e.get("link", otsikko)),
            "ticker": ticker,
            "tyyppi": "uutinen",
            "lahde": "Google News",
            "otsikko": otsikko,
            "url": e.get("link", ""),
            "julkaistu": e.get("published", ""),
        })
    return tulokset


def yahoo_rss(ticker: str) -> list[dict]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
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


def teema_uutiset(teema: str, haku: str) -> list[dict]:
    """Hakee laajasti uutisia yhdestä pullonkaula-teemasta (ei sidottu tickeriin)."""
    q = requests.utils.quote(f"{haku} when:3d")
    url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(url)
    except Exception:
        return []
    tulokset = []
    for e in feed.entries[:14]:
        otsikko = e.get("title", "")
        if not otsikko:
            continue
        tulokset.append({
            "id": _id("teema", teema, e.get("link", otsikko)),
            "teema": teema,
            "tyyppi": "teema",
            "lahde": "Google News",
            "otsikko": otsikko,
            "url": e.get("link", ""),
            "julkaistu": e.get("published", ""),
        })
    return tulokset


# --- Some --------------------------------------------------------------------

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
        if teksti:
            viestit.append({"id": _id("st", str(m.get("id", teksti))), "lahde": "StockTwits", "teksti": teksti[:500]})
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
        if teksti:
            viestit.append({"id": _id("rd", d.get("id", teksti)), "lahde": "Reddit", "teksti": teksti[:500]})
    return viestit


# --- Viralliset tiedotteet ---------------------------------------------------

_CIK_VALIMUISTI: dict[str, str] | None = None


def _cik_kartta() -> dict[str, str]:
    global _CIK_VALIMUISTI
    if _CIK_VALIMUISTI is not None:
        return _CIK_VALIMUISTI
    _CIK_VALIMUISTI = {}
    try:
        r = requests.get("https://www.sec.gov/files/company_tickers.json", headers=SEC_UA, timeout=20)
        if r.status_code == 200:
            for rivi in r.json().values():
                _CIK_VALIMUISTI[rivi["ticker"].upper()] = str(rivi["cik_str"]).zfill(10)
    except Exception:
        pass
    return _CIK_VALIMUISTI


def sec_tiedotteet(ticker: str) -> list[dict]:
    """Yhdysvaltalaisen yhtiön viralliset SEC-tiedotteet (8-K = olennainen tapahtuma, 10-Q/10-K/6-K = tulos)."""
    cik = _cik_kartta().get(ticker.upper())
    if not cik:
        return []
    url = (
        "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany"
        f"&CIK={cik}&type=&dateb=&owner=include&count=15&output=atom"
    )
    try:
        feed = feedparser.parse(url, request_headers=SEC_UA)
    except Exception:
        return []
    raja = datetime.now(timezone.utc) - timedelta(days=4)
    tulokset = []
    for e in feed.entries[:15]:
        pvm = e.get("updated_parsed") or e.get("published_parsed")
        if pvm and datetime(*pvm[:6], tzinfo=timezone.utc) < raja:
            continue
        laji = (e.get("title", "") or "").strip()
        tulokset.append({
            "id": _id("sec", ticker, e.get("link", laji)),
            "ticker": ticker,
            "tyyppi": "tiedote",
            "lahde": f"SEC ({laji.split(' - ')[0]})",
            "otsikko": f"Virallinen tiedote: {laji}",
            "url": e.get("link", ""),
            "julkaistu": e.get("updated", ""),
        })
    return tulokset


def asx_tiedotteet(koodi: str) -> list[dict]:
    """Australian pörssin viralliset yhtiötiedotteet."""
    url = f"https://asx.api.markitdigital.com/asx-research/1.0/companies/{koodi}/announcements?count=15&pageSize=15"
    try:
        r = requests.get(url, headers=UA, timeout=20)
        if r.status_code != 200:
            return []
        data = r.json().get("data", {})
    except Exception:
        return []
    rivit = data.get("items") if isinstance(data, dict) else None
    if not rivit:
        return []
    raja = datetime.now(timezone.utc) - timedelta(days=4)
    tulokset = []
    for a in rivit[:15]:
        otsikko = a.get("headerFormatted") or a.get("header") or ""
        pvm_str = a.get("date") or a.get("documentDate") or ""
        try:
            if pvm_str and datetime.fromisoformat(pvm_str.replace("Z", "+00:00")) < raja:
                continue
        except ValueError:
            pass
        if not otsikko:
            continue
        tulokset.append({
            "id": _id("asx", koodi, str(a.get("id", otsikko))),
            "ticker": f"{koodi}.AX",
            "tyyppi": "tiedote",
            "lahde": "ASX-tiedote",
            "otsikko": f"Virallinen tiedote: {otsikko}",
            "url": a.get("url", ""),
            "julkaistu": pvm_str,
        })
    return tulokset


# --- Kurssit -----------------------------------------------------------------

def kurssi(ticker: str) -> dict | None:
    """Viimeisin kurssi ja muutos 1 pv / 5 pv Yahoo Financen chart-rajapinnasta."""
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1mo&interval=1d"
    try:
        r = requests.get(url, headers=UA, timeout=20)
        if r.status_code != 200:
            return None
        tulos = r.json()["chart"]["result"][0]
        suljut = [c for c in tulos["indicators"]["quote"][0]["close"] if c is not None]
        valuutta = tulos.get("meta", {}).get("currency", "")
    except Exception:
        return None
    if len(suljut) < 2:
        return None

    def muutos(n: int) -> float | None:
        if len(suljut) <= n:
            return None
        vanha = suljut[-1 - n]
        return round(100 * (suljut[-1] - vanha) / vanha, 1) if vanha else None

    return {"hinta": round(suljut[-1], 2), "valuutta": valuutta, "muutos_1pv": muutos(1), "muutos_5pv": muutos(5)}


# --- Tuloskalenteri (valinnainen, vaatii ilmaisen Finnhub-avaimen) ----------

def tulospaiva(ticker: str) -> dict | None:
    if not config.FINNHUB_KEY:
        return None
    tanaan = datetime.now(timezone.utc).date()
    url = (
        "https://finnhub.io/api/v1/calendar/earnings"
        f"?from={tanaan}&to={tanaan + timedelta(days=45)}&symbol={ticker}&token={config.FINNHUB_KEY}"
    )
    try:
        r = requests.get(url, timeout=20)
        if r.status_code != 200:
            return None
        rivit = r.json().get("earningsCalendar", [])
    except Exception:
        return None
    if not rivit:
        return None
    seuraava = sorted(rivit, key=lambda x: x.get("date", ""))[0]
    return {"paiva": seuraava.get("date", ""), "arvio_eps": seuraava.get("epsEstimate")}
