"""Pääkerääjä: uutiset, viralliset tiedotteet, some, kurssit ja tuloskalenteri.

Ajo:              python -m src.collector
Ajo + kooste:     python -m src.collector --digest
Ajo + teemat:     python -m src.collector --themes
"""
import argparse
import json
import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from . import classifier, config, notifier, sources


def _lataa(polku: str, oletus):
    try:
        with open(polku, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return oletus


def _tallenna(polku: str, data) -> None:
    os.makedirs(os.path.dirname(polku), exist_ok=True)
    with open(polku, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def _kohde(nimi: str) -> str:
    return os.path.join(config.DATA_DIR, nimi)


def kerää_watchlist(watchlist, nahdyt_set, nahdyt, nyt) -> list[dict]:
    """Uutiset, viralliset tiedotteet ja some-koonnit — luokiteltuina."""
    uudet_uutiset, some = [], {}
    for osake in watchlist:
        ticker, nimi = osake["ticker"], osake["nimi"]
        lahteet = sources.google_news(ticker, nimi) + sources.yahoo_rss(ticker)
        if osake.get("markkina") == "asx" and osake.get("asx_koodi"):
            lahteet += sources.asx_tiedotteet(osake["asx_koodi"])
        else:
            lahteet += sources.sec_tiedotteet(ticker)
        for item in lahteet:
            if item["id"] not in nahdyt_set:
                nahdyt_set.add(item["id"]); nahdyt.append(item["id"])
                uudet_uutiset.append(item)
        viestit = [v for v in sources.stocktwits(osake.get("stocktwits", ticker)) + sources.reddit(ticker, nimi)
                   if v["id"] not in nahdyt_set]
        if len(viestit) >= config.SOME_MIN_VIESTIT:
            some[ticker] = viestit
            for v in viestit:
                nahdyt_set.add(v["id"]); nahdyt.append(v["id"])

    lisattavat = []
    if uudet_uutiset:
        arviot = classifier.luokittele_uutiset(uudet_uutiset)
        for u in uudet_uutiset:
            a = arviot.get(u["id"], {})
            u.update(kriittisyys=int(a.get("kriittisyys", 3)), luokka=a.get("luokka", "muu"),
                     tiivistelma=a.get("tiivistelma", ""), haettu=nyt)
            lisattavat.append(u)
    for osake in watchlist:
        ticker = osake["ticker"]
        if ticker not in some:
            continue
        k = classifier.koosta_some(ticker, osake["nimi"], some[ticker])
        lisattavat.append({
            "id": f"some-{ticker}-{nyt}", "ticker": ticker, "tyyppi": "some-koonti",
            "lahde": "StockTwits/Reddit",
            "otsikko": f"Sijoittajakeskustelun kooste ({len(some[ticker])} viestiä, tunnelma: {k.get('tunnelma', 'neutraali')})",
            "url": "", "julkaistu": nyt, "kriittisyys": int(k.get("kriittisyys", 3)),
            "luokka": "some", "tiivistelma": k.get("tiivistelma", ""), "haettu": nyt,
        })
    return lisattavat


def kerää_kurssit(watchlist, nyt) -> None:
    markkinat = {}
    for osake in watchlist:
        k = sources.kurssi(osake["ticker"])
        if k:
            k["nimi"] = osake["nimi"]
            tulos = sources.tulospaiva(osake["ticker"])
            if tulos:
                k["tulospaiva"] = tulos.get("paiva")
            markkinat[osake["ticker"]] = k
    if markkinat:
        _tallenna(_kohde("markkinat.json"), {"paivitetty": nyt, "kurssit": markkinat})


def kerää_teemat(nahdyt_set, nahdyt, nyt) -> None:
    kaikki = []
    for t in config.TEEMAT:
        for item in sources.teema_uutiset(t["nimi"], t["haku"]):
            if item["id"] not in nahdyt_set:
                nahdyt_set.add(item["id"]); nahdyt.append(item["id"])
                kaikki.append(item)
    if not kaikki:
        return
    arviot = classifier.luokittele_teemat(kaikki)
    edellinen = _lataa(_kohde("teemat.json"), {})
    uutiset_per_teema = defaultdict(list)
    for vanha in edellinen.get("uutiset", []):
        uutiset_per_teema[vanha["teema"]].append(vanha)
    yhtiot = {y["nimi"].lower(): y for y in edellinen.get("yhtiot", [])}

    for u in kaikki:
        a = arviot.get(u["id"], {})
        if not a.get("relevantti"):
            continue
        u.update(kriittisyys=int(a.get("kriittisyys", 3)), tiivistelma=a.get("tiivistelma", ""), haettu=nyt)
        uutiset_per_teema[u["teema"]].insert(0, u)
        for y in a.get("yhtiot", []):
            avain = (y.get("nimi") or "").lower().strip()
            if not avain:
                continue
            rivi = yhtiot.setdefault(avain, {"nimi": y["nimi"], "ticker": y.get("ticker", ""), "mainintoja": 0, "teemat": []})
            rivi["mainintoja"] += 1
            if y.get("ticker") and not rivi.get("ticker"):
                rivi["ticker"] = y["ticker"]
            if u["teema"] not in rivi["teemat"]:
                rivi["teemat"].append(u["teema"])

    teema_lista, kaikki_uutiset = [], []
    for t in config.TEEMAT:
        lista = uutiset_per_teema.get(t["nimi"], [])[:12]
        teema_lista.append({"nimi": t["nimi"], "maara": len(lista)})
        kaikki_uutiset += lista
    yhteensa = sum(x["maara"] for x in teema_lista) or 1
    for x in teema_lista:
        x["osuus"] = round(100 * x["maara"] / yhteensa)

    watchlist_tickerit = {o["ticker"].split(".")[0].upper() for o in _lataa(config.WATCHLIST, {"osakkeet": []})["osakkeet"]}
    uudet_yhtiot = sorted(
        (y for y in yhtiot.values()
         if y.get("ticker") and y["ticker"].upper() not in watchlist_tickerit and y["mainintoja"] >= 2),
        key=lambda y: -y["mainintoja"],
    )[:20]

    _tallenna(_kohde("teemat.json"), {
        "paivitetty": nyt, "teemat": teema_lista,
        "uutiset": kaikki_uutiset[:config.MAX_TEEMAUUTISIA],
        "yhtiot": sorted(yhtiot.values(), key=lambda y: -y["mainintoja"])[:80],
        "uudet_ehdokkaat": uudet_yhtiot,
    })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest", action="store_true")
    parser.add_argument("--themes", action="store_true")
    args = parser.parse_args()

    watchlist = _lataa(config.WATCHLIST, {"osakkeet": []})["osakkeet"]
    nyt = datetime.now(timezone.utc).isoformat(timespec="seconds")
    uutiset = _lataa(_kohde("uutiset.json"), [])
    nahdyt = _lataa(_kohde("nahdyt.json"), [])
    nahdyt_set = set(nahdyt)

    lisattavat = kerää_watchlist(watchlist, nahdyt_set, nahdyt, nyt)
    print(f"Uusia uutisia/tiedotteita/koonteja: {len(lisattavat)}")
    if lisattavat:
        uutiset = (lisattavat + uutiset)[:config.MAX_UUTISIA_MUISTISSA]
    _tallenna(_kohde("uutiset.json"), uutiset)

    kerää_kurssit(watchlist, nyt)

    if args.themes:
        kerää_teemat(nahdyt_set, nahdyt, nyt)
        print("Teemauutiset päivitetty.")

    _tallenna(_kohde("nahdyt.json"), nahdyt[-config.MAX_NAHTYJA:])

    kriittiset = [u for u in lisattavat if u.get("kriittisyys", 0) >= config.HALYTYSKYNNYS]
    if kriittiset:
        notifier.laheta_halytys(kriittiset)

    if args.digest:
        raja = datetime.now(timezone.utc) - timedelta(hours=24)
        koosteeseen = []
        for u in uutiset:
            try:
                haettu = datetime.fromisoformat(u.get("haettu", ""))
            except ValueError:
                continue
            if haettu >= raja and config.KOOSTEKYNNYS <= u.get("kriittisyys", 0) < config.HALYTYSKYNNYS:
                koosteeseen.append(u)
        if koosteeseen:
            notifier.laheta_kooste(koosteeseen)
        else:
            print("Ei koostettavaa viimeisen 24 h ajalta.")


if __name__ == "__main__":
    main()
