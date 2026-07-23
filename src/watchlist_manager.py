"""Automaattinen seurantalistan hallinta.

Lisää uusia yhtiöitä, kun ne nousevat esiin analyysissä ja uutisissa, ja poistaa
automaattilisättyjä yhtiöitä, jotka ovat hiljentyneet. Omia osakkeita (lahde="oma")
ei koskaan poisteta. Ajo: python -m src.watchlist_manager
"""
import json
import os
from datetime import datetime, timedelta, timezone

from . import config, notifier


def _lataa(polku, oletus):
    try:
        with open(polku, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return oletus


def _tallenna(polku, data):
    os.makedirs(os.path.dirname(polku), exist_ok=True)
    with open(polku, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def _norm(t: str) -> str:
    return (t or "").strip().upper()


def _markkina(ticker: str) -> dict | None:
    """Päättele markkina tickeristä. Palauta None jos lähteemme eivät tue sitä."""
    t = _norm(ticker)
    if not t:
        return None
    if t.endswith(".AX"):
        return {"markkina": "asx", "asx_koodi": t[:-3], "stocktwits": t}
    if "." in t:
        return None  # muut pörssit (esim. .PA, .DE) — lähteemme ovat US/ASX-painotteisia
    return {"markkina": "us", "stocktwits": t}


def _ehdokkaat() -> dict[str, dict]:
    """Kerää lisättävät ehdokkaat analyysistä ja teemauutisista."""
    analyysi = _lataa(os.path.join(config.DATA_DIR, "analyysi.json"), {}).get("data", {})
    teemat = _lataa(os.path.join(config.DATA_DIR, "teemat.json"), {})
    ehdokkaat: dict[str, dict] = {}

    for e in analyysi.get("uudet_ehdokkaat", []):
        t = _norm(e.get("ticker"))
        if t:
            ehdokkaat[t] = {"ticker": t, "nimi": e.get("nimi", t), "syy": f"Analyysi: {e.get('miksi', 'nostettu seurantaehdokkaaksi')}"[:180]}

    for y in teemat.get("uudet_ehdokkaat", []):
        t = _norm(y.get("ticker"))
        if t and y.get("mainintoja", 0) >= config.AUTO_LISAYS_MAINTA and t not in ehdokkaat:
            teemat_str = ", ".join(y.get("teemat", []))
            ehdokkaat[t] = {"ticker": t, "nimi": y.get("nimi", t), "syy": f"Uutisvirta: {y['mainintoja']} mainintaa ({teemat_str})"[:180]}

    return ehdokkaat


def _hiljainen(ticker: str, uutiset: list[dict], nyt: datetime) -> bool:
    raja = nyt - timedelta(days=config.AUTO_POISTO_PAIVAT)
    for u in uutiset:
        if u.get("ticker") != ticker:
            continue
        try:
            if datetime.fromisoformat(u.get("haettu", "")) >= raja:
                return False
        except ValueError:
            continue
    return True


def main() -> None:
    if not config.AUTO_SEURANTA:
        print("Automaattiseuranta pois päältä.")
        return

    watchlist = _lataa(config.WATCHLIST, {"osakkeet": []})
    osakkeet = watchlist.get("osakkeet", [])
    uutiset = _lataa(os.path.join(config.DATA_DIR, "uutiset.json"), [])
    nyt = datetime.now(timezone.utc)
    nyt_str = nyt.isoformat(timespec="seconds")
    seurannassa = {_norm(o["ticker"]) for o in osakkeet}
    muutokset = []

    # --- Poistot: vain automaattilisätyt, jotka ovat hiljentyneet armonajan jälkeen ---
    jaljelle = []
    for o in osakkeet:
        if o.get("lahde") == "auto":
            try:
                lisatty = datetime.fromisoformat(o.get("lisatty", nyt_str))
            except ValueError:
                lisatty = nyt
            armon_jalkeen = (nyt - lisatty) >= timedelta(days=config.AUTO_POISTO_PAIVAT)
            if armon_jalkeen and _hiljainen(_norm(o["ticker"]), uutiset, nyt):
                muutokset.append({"tyyppi": "poisto", "ticker": o["ticker"], "nimi": o.get("nimi", ""),
                                  "syy": f"Ei uutisia {config.AUTO_POISTO_PAIVAT} päivään", "aika": nyt_str})
                seurannassa.discard(_norm(o["ticker"]))
                continue
        jaljelle.append(o)
    osakkeet = jaljelle

    # --- Lisäykset: ehdokkaat, jotka eivät jo ole listalla, kokorajaan asti ---
    for t, e in _ehdokkaat().items():
        if len(osakkeet) >= config.AUTO_MAX:
            break
        if t in seurannassa:
            continue
        mkt = _markkina(t)
        if not mkt:
            continue
        uusi = {"ticker": t, "nimi": e["nimi"], "lahde": "auto", "lisatty": nyt_str, "syy": e["syy"], **mkt}
        osakkeet.append(uusi)
        seurannassa.add(t)
        muutokset.append({"tyyppi": "lisays", "ticker": t, "nimi": e["nimi"], "syy": e["syy"], "aika": nyt_str})

    watchlist["osakkeet"] = osakkeet
    _tallenna(config.WATCHLIST, watchlist)

    loki = _lataa(os.path.join(config.DATA_DIR, "seurantamuutokset.json"), {"muutokset": []})
    loki = {"paivitetty": nyt_str, "muutokset": (muutokset + loki.get("muutokset", []))[:50]}
    _tallenna(os.path.join(config.DATA_DIR, "seurantamuutokset.json"), loki)

    # Tilannekuva dashboardille (repojuuren watchlist.json ei näy Pages-sivustolla)
    _tallenna(os.path.join(config.DATA_DIR, "seuranta.json"), {
        "paivitetty": nyt_str,
        "osakkeet": [{"ticker": o["ticker"], "nimi": o.get("nimi", ""),
                      "lahde": o.get("lahde", "oma"), "syy": o.get("syy", ""),
                      "lisatty": o.get("lisatty", "")} for o in osakkeet],
    })

    lisatyt = [m for m in muutokset if m["tyyppi"] == "lisays"]
    poistetut = [m for m in muutokset if m["tyyppi"] == "poisto"]
    print(f"Seurantalista: +{len(lisatyt)} / -{len(poistetut)}, yhteensä {len(osakkeet)} yhtiötä.")
    if muutokset:
        notifier.laheta_seurantamuutokset(lisatyt, poistetut)


if __name__ == "__main__":
    main()
