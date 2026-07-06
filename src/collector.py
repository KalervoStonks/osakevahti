"""Pääohjelma: hakee uutiset ja someviestit, luokittelee uudet ja lähettää ilmoitukset.

Ajo:            python -m src.collector
Ajo + kooste:   python -m src.collector --digest
"""
import argparse
import json
import os
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--digest", action="store_true", help="lähetä myös päivän kooste")
    args = parser.parse_args()

    watchlist = _lataa(config.WATCHLIST, {"osakkeet": []})["osakkeet"]
    uutiset_polku = os.path.join(config.DATA_DIR, "uutiset.json")
    nahdyt_polku = os.path.join(config.DATA_DIR, "nahdyt.json")
    uutiset: list[dict] = _lataa(uutiset_polku, [])
    nahdyt: list[str] = _lataa(nahdyt_polku, [])
    nahdyt_set = set(nahdyt)
    nyt = datetime.now(timezone.utc).isoformat(timespec="seconds")

    uudet_uutiset: list[dict] = []
    uudet_someviestit: dict[str, list[dict]] = {}

    for osake in watchlist:
        ticker, nimi = osake["ticker"], osake["nimi"]
        for item in sources.google_news(ticker, nimi) + sources.yahoo_rss(ticker):
            if item["id"] not in nahdyt_set:
                nahdyt_set.add(item["id"])
                nahdyt.append(item["id"])
                uudet_uutiset.append(item)
        viestit = [
            v for v in sources.stocktwits(osake.get("stocktwits", ticker)) + sources.reddit(ticker, nimi)
            if v["id"] not in nahdyt_set
        ]
        if len(viestit) >= config.SOME_MIN_VIESTIT:
            uudet_someviestit[ticker] = viestit
            for v in viestit:
                nahdyt_set.add(v["id"])
                nahdyt.append(v["id"])

    print(f"Uusia uutisia: {len(uudet_uutiset)}, some-koonteja: {len(uudet_someviestit)}")

    lisattavat: list[dict] = []

    if uudet_uutiset:
        arviot = classifier.luokittele_uutiset(uudet_uutiset)
        for u in uudet_uutiset:
            arvio = arviot.get(u["id"], {})
            u["kriittisyys"] = int(arvio.get("kriittisyys", 3))
            u["luokka"] = arvio.get("luokka", "muu")
            u["tiivistelma"] = arvio.get("tiivistelma", "")
            u["haettu"] = nyt
            lisattavat.append(u)

    for osake in watchlist:
        ticker = osake["ticker"]
        if ticker not in uudet_someviestit:
            continue
        viestit = uudet_someviestit[ticker]
        koonti = classifier.koosta_some(ticker, osake["nimi"], viestit)
        lisattavat.append({
            "id": f"some-{ticker}-{nyt}",
            "ticker": ticker,
            "tyyppi": "some-koonti",
            "lahde": "StockTwits/Reddit",
            "otsikko": f"Sijoittajakeskustelun kooste ({len(viestit)} viestiä, tunnelma: {koonti.get('tunnelma', 'neutraali')})",
            "url": "",
            "julkaistu": nyt,
            "kriittisyys": int(koonti.get("kriittisyys", 3)),
            "luokka": "some",
            "tiivistelma": koonti.get("tiivistelma", ""),
            "haettu": nyt,
        })

    if lisattavat:
        uutiset = lisattavat + uutiset
        uutiset = uutiset[:config.MAX_UUTISIA_MUISTISSA]

    _tallenna(uutiset_polku, uutiset)
    _tallenna(nahdyt_polku, nahdyt[-config.MAX_NAHTYJA:])

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
