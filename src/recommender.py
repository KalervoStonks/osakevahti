"""Tekoälyn tuottama sijoitusnäkemys jokaisesta seurattavasta yhtiöstä.

EI ole sijoitusneuvontaa: malli tekee omat päätelmänsä julkisesta datasta ja
tunnistaa yhtiötyypin, jotta tunnusluvut tulkitaan oikein. Ajo: python -m src.recommender
"""
import json
import os
import re
from datetime import datetime, timezone

import anthropic

from . import config


def _lataa(polku: str, oletus):
    try:
        with open(polku, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return oletus


OHJE = """Olet kokenut osakeanalyytikko, joka kirjoittaa suomenkieliselle yksityissijoittajalle. Tehtäväsi on muodostaa itsenäinen, perusteltu näkemys jokaisesta annetusta yhtiöstä julkisen tiedon pohjalta. Käytä verkkohakua hakeaksesi kunkin yhtiön tuoreimmat tunnusluvut ja olennaiset viimeaikaiset tapahtumat. ÄLÄ kopioi valmiita analyytikkosuosituksia netistä — muodosta oma päätelmäsi.

Kriittistä: tunnista ensin kunkin yhtiön TYYPPI ja sovella sille oikeita mittareita:
- Tuottamaton kaivos-/exploraatioyhtiö: mineraalivarannot ja pitoisuudet, luvat, rahoitustilanne ja kassan riittävyys (runway), rahanpolttonopeus, mahdolliset osto-/toimitussopimukset, laimennusriski. ÄLÄ käytä P/E-lukua.
- Raaka-ainetuottaja: tuotantokustannus (AISC), raaka-aineen hinta, myyntisopimukset vs. spot, reservit, kysyntänäkymä.
- Syklinen puolijohdeyhtiö: missä kohtaa sykliä ollaan, varastotasot, muistin/komponenttien hinnat, käyttökate ja sen suunta, investoinnit, kysyntä-tarjonta.
- Rakenteellinen kasvuyhtiö: liikevaihdon kasvu, kasvun ja arvostuksen suhde (esim. PEG, forward P/E vs. kasvu), käyttökate, markkinan koko ja kilpailuetu, tilauskanta. Korkea arvostuskerroin voi olla perusteltu kovan kasvun takia, mutta huomioi arvostusriski.
- Vakiintunut arvoyhtiö: P/E, osinko, vapaa kassavirta, tase ja velkaisuus.

Palauta jokaiselle yhtiölle:
- nakemys: yksi näistä: "Osta", "Lisää", "Pidä", "Vähennä", "Myy"
- varmuus: "matala", "keskitaso" tai "korkea" (kuinka luotettavaa julkinen data ja näkymä on)
- tyyppi: lyhyt kuvaus yhtiötyypistä (esim. "syklinen muistivalmistaja")
- teesi: 2-3 virkettä ydinnäkemyksestä
- harka: 2-4 lyhyttä pointtia puolesta
- karhu: 2-4 lyhyttä pointtia vastaan
- tunnusluvut: 3-6 keskeistä lukua tulkintoineen, kukin {mittari, arvo, tulkinta}. Merkitse arvioksi jos et löytänyt tarkkaa lukua.
- katalyytit: 1-3 tulevaa tapahtumaa jotka voivat liikuttaa kurssia
- riskit: 2-3 keskeistä riskiä
- aikajanne: esim. "6-18 kk"

Kirjoita kaikki suomeksi, tiiviisti ja konkreettisesti. Palauta vastauksen lopussa VAIN yksi JSON-lohko:

```json
{ "yhtiot": [ { "ticker": "...", "nimi": "...", "nakemys": "...", "varmuus": "...", "tyyppi": "...", "teesi": "...", "harka": ["..."], "karhu": ["..."], "tunnusluvut": [{"mittari":"...","arvo":"...","tulkinta":"..."}], "katalyytit": ["..."], "riskit": ["..."], "aikajanne": "..." } ] }
```"""


def _valitut(watchlist: list[dict], uutiset: list[dict]) -> list[dict]:
    """Omat osakkeet ensin, sitten automaattiset uutisaktiivisuuden mukaan — kokorajaan asti."""
    maara = {}
    for u in uutiset:
        maara[u.get("ticker")] = maara.get(u.get("ticker"), 0) + 1
    omat = [o for o in watchlist if o.get("lahde") != "auto"]
    autot = sorted((o for o in watchlist if o.get("lahde") == "auto"),
                   key=lambda o: -maara.get(o["ticker"], 0))
    return (omat + autot)[:config.REKISTERI_MAX]


def _konteksti() -> str:
    watchlist = _lataa(config.WATCHLIST, {"osakkeet": []})["osakkeet"]
    uutiset = _lataa(os.path.join(config.DATA_DIR, "uutiset.json"), [])
    markkinat = _lataa(os.path.join(config.DATA_DIR, "markkinat.json"), {}).get("kurssit", {})
    osat = ["Seurattavat yhtiöt ja niiden tuore konteksti:\n"]
    for o in _valitut(watchlist, uutiset):
        t = o["ticker"]
        k = markkinat.get(t, {})
        kurssi = f"{k.get('hinta')} {k.get('valuutta','')} (1pv {k.get('muutos_1pv')} %, 5pv {k.get('muutos_5pv')} %)" if k else "ei kurssidataa"
        otsikot = [u["otsikko"] for u in uutiset if u.get("ticker") == t and u.get("kriittisyys", 0) >= 4][:5]
        osat.append(f"\n{o['nimi']} ({t}) — kurssi: {kurssi}")
        for otsikko in otsikot:
            osat.append(f"  - {otsikko}")
    osat.append("\nHae verkosta kunkin yhtiön tuoreet tunnusluvut ja muodosta näkemys.")
    return "\n".join(osat)


def main() -> None:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": _konteksti()}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 12}]

    resp = None
    for _ in range(8):
        resp = client.messages.create(
            model=config.MALLI_SUOSITUS, max_tokens=16000,
            output_config={"effort": "medium"}, system=OHJE, tools=tools, messages=messages,
        )
        if resp.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": resp.content})

    teksti = "\n".join(b.text for b in resp.content if b.type == "text")
    osuma = re.search(r"```json\s*(\{.*\})\s*```", teksti, re.DOTALL)
    data = {}
    if osuma:
        try:
            data = json.loads(osuma.group(1))
        except json.JSONDecodeError:
            print("Varoitus: suositus-JSON:n jäsennys epäonnistui.")

    tulos = {"paivitetty": datetime.now(timezone.utc).isoformat(timespec="seconds"),
             "yhtiot": data.get("yhtiot", [])}
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(os.path.join(config.DATA_DIR, "suositukset.json"), "w", encoding="utf-8") as f:
        json.dump(tulos, f, ensure_ascii=False, indent=1)
    print(f"Suositukset tallennettu: {len(tulos['yhtiot'])} yhtiötä")


if __name__ == "__main__":
    main()
