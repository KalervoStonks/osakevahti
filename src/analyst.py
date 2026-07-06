"""Viikoittainen AI-pullonkaula-analyysi: Claude + web-haku.

Ajo: python -m src.analyst
"""
import json
import os
import re
from datetime import datetime, timezone

import anthropic

from . import config, notifier


def _lataa_watchlist() -> list[dict]:
    with open(config.WATCHLIST, encoding="utf-8") as f:
        return json.load(f)["osakkeet"]


def _tehtava(watchlist: list[dict]) -> str:
    lista = ", ".join(f'{o["nimi"]} ({o["ticker"]})' for o in watchlist)
    return f"""Olet kokenut sijoitusanalyytikko. Selvitä verkkohaulla, mitkä ovat tekoälyn kehityksen ja käyttöönoton merkittävimmät pullonkaulat juuri nyt, ja jäsennä ne liiketoiminta-alueittain. Tyypillisiä alueita ovat esimerkiksi: laskentakapasiteetti ja sirut, muisti (HBM/DRAM), energia ja sähköverkot, ydinvoima ja uraani, jäähdytys, verkotus ja optiikka, kriittiset mineraalit, datakeskusrakentaminen, data ja ohjelmistot — mutta valitse alueet sen mukaan mikä on ajankohtaista.

Jokaiselle alueelle:
1. Kuvaus pullonkaulasta ja sen kehityssuunnasta (kiristyykö vai helpottaako).
2. Keskeiset suuret yhtiöt, jotka hyötyvät tai ratkovat ongelmaa.
3. 1-3 pienempää korkean tuottopotentiaalin yhtiötä: ticker, lyhyt sijoitusperustelu ja keskeiset riskit. Suosi yhtiöitä, joista on tuoretta konkreettista uutisvirtaa.

Huomioi erikseen seurantalistan yhtiöt: {lista}. Kerro jokaisesta, mihin pullonkaulaan se liittyy ja mitä olennaista siitä on uutisoitu viime aikoina.

Nosta lopuksi esiin uudet seurantaehdokkaat: yhtiöt joita ei vielä ole seurantalistalla mutta jotka uutisvirran perusteella ansaitsisivat paikan.

Kirjoita kaikki tekstit suomeksi. Palauta vastauksen lopussa JSON-lohko muodossa:

```json
{{
  "yleiskuva": "3-5 virkkeen tilannekuva",
  "alueet": [
    {{
      "nimi": "...",
      "kuvaus": "...",
      "suuret_yhtiot": ["Nimi (TICKER)"],
      "pienet_poiminnat": [
        {{"ticker": "...", "nimi": "...", "perustelu": "...", "riskit": "..."}}
      ]
    }}
  ],
  "seurantalista": [
    {{"ticker": "...", "liittyy": "mihin pullonkaulaan", "huomiot": "tuoreet olennaiset uutiset"}}
  ],
  "uudet_ehdokkaat": [
    {{"ticker": "...", "nimi": "...", "miksi": "..."}}
  ]
}}
```"""


def main() -> None:
    watchlist = _lataa_watchlist()
    client = anthropic.Anthropic()

    messages = [{"role": "user", "content": _tehtava(watchlist)}]
    tools = [{"type": "web_search_20260209", "name": "web_search", "max_uses": 8}]

    resp = None
    for _ in range(6):
        resp = client.messages.create(
            model=config.MALLI_ANALYYSI,
            max_tokens=16000,
            output_config={"effort": "medium"},
            tools=tools,
            messages=messages,
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
            print("Varoitus: JSON-lohkon jäsennys epäonnistui, tallennetaan vain teksti.")

    tulos = {
        "paivitetty": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data": data,
    }
    polku = os.path.join(config.DATA_DIR, "analyysi.json")
    os.makedirs(config.DATA_DIR, exist_ok=True)
    with open(polku, "w", encoding="utf-8") as f:
        json.dump(tulos, f, ensure_ascii=False, indent=1)
    print(f"Analyysi tallennettu: {polku}")

    yleiskuva = data.get("yleiskuva", "")
    ehdokkaat = data.get("uudet_ehdokkaat", [])
    if yleiskuva:
        rivit = "".join(
            f'<li><strong>{e.get("nimi", "")} ({e.get("ticker", "")})</strong>: {e.get("miksi", "")}</li>'
            for e in ehdokkaat
        )
        html = (
            f"<h2>Viikon AI-pullonkaula-analyysi</h2><p>{yleiskuva}</p>"
            + (f"<h3>Uudet seurantaehdokkaat</h3><ul>{rivit}</ul>" if rivit else "")
            + "<p>Koko analyysi dashboardin Pullonkaulat-välilehdellä.</p>"
        )
        notifier.laheta("Osakevahti: viikon AI-pullonkaula-analyysi", html)


if __name__ == "__main__":
    main()
