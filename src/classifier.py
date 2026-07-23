"""Uutisten luokittelu, some-koonnit ja teemauutisten jäsentäminen Claude Haikulla."""
import json

import anthropic

from . import config


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


LUOKITTELU_OHJE = """Olet suomalaisen yksityissijoittajan uutisvahti. Saat JSON-listan otsikoita seurattavista osakkeista (uutisia ja virallisia pörssitiedotteita). Arvioi jokainen:

- kriittisyys, kokonaisluku 1-10:
  9-10 = vaikuttaa välittömästi sijoituspäätökseen: tulosvaroitus, yrityskauppa tai ostotarjous, osake- tai lainaemissio, merkittävä uusi sopimus tai tilaus, kriittinen viranomaispäätös, toimitusjohtajan äkillinen lähtö.
  6-8 = merkittävä: tulosjulkistus, ohjeistuksen muutos, iso analyytikkosuosituksen muutos, merkittävä tuotejulkistus, olennainen toimialakäänne.
  3-5 = tavanomainen yhtiö- tai toimialauutinen.
  1-2 = vähäpätöinen, spekulatiivinen listausartikkeli tai mainosmainen sisältö.
- luokka: yksi näistä: tulos, yrityskauppa, sopimus, tuote, johto, saantely, rahoitus, analyytikko, toimiala, muu
- tiivistelma: 1-2 virkettä suomeksi: mitä tapahtui ja miksi sillä on väliä sijoittajalle.

Viralliset pörssitiedotteet (SEC/ASX) ovat lähtökohtaisesti tärkeämpiä kuin lehtijutut. Jos otsikko ei oikeasti koske kyseistä yhtiötä, anna kriittisyys 1. Palauta arvio jokaiselle id:lle."""

LUOKITTELU_SCHEMA = {
    "type": "object",
    "properties": {
        "arviot": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "kriittisyys": {"type": "integer"},
                    "luokka": {"type": "string"},
                    "tiivistelma": {"type": "string"},
                },
                "required": ["id", "kriittisyys", "luokka", "tiivistelma"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["arviot"],
    "additionalProperties": False,
}

SOME_OHJE = """Olet sijoittajan somevahti. Saat tuoreita sijoittajaviestejä (StockTwits/Reddit) yhdestä osakkeesta. Koosta:

- tiivistelma: 2-4 virkettä suomeksi keskustelun olennaisimmista pointeista: toistuvat väitteet, huhut, konkreettiset tapahtumat, yleistunnelma. Älä listaa yksittäisiä viestejä.
- tunnelma: positiivinen, neutraali tai negatiivinen
- kriittisyys 1-10: anna yli 7 vain jos viesteissä toistuu konkreettinen, merkittävä ja uusi tieto. Tavallinen kurssispekulaatio on korkeintaan 4."""

SOME_SCHEMA = {
    "type": "object",
    "properties": {
        "tiivistelma": {"type": "string"},
        "tunnelma": {"type": "string"},
        "kriittisyys": {"type": "integer"},
    },
    "required": ["tiivistelma", "tunnelma", "kriittisyys"],
    "additionalProperties": False,
}

TEEMA_OHJE = """Olet tekoälyn pullonkauloja seuraava sijoitusanalyytikko. Saat uutisotsikoita, jotka on haettu tietystä pullonkaula-teemasta (esim. jäähdytys, muisti, kriittiset mineraalit). Arvioi jokainen otsikko:

- relevantti: true vain jos otsikko oikeasti käsittelee tekoälyn/datakeskusten rakentamisen pullonkaulaa. Yleiset markkinakatsaukset ja mainosmaiset "top 5 osaketta" -listat -> false.
- kriittisyys 1-10: kuinka merkittävä signaali pullonkaulasta (uusi kapasiteetti, pula, iso sopimus, teknologiaharppaus = korkea).
- tiivistelma: 1 virke suomeksi.
- yhtiot: lista pörssiyhtiöistä jotka otsikossa mainitaan tai jotka selvästi liittyvät. Jokaiselle {nimi, ticker}. Anna ticker vain jos tunnet sen varmasti (esim. Nvidia -> NVDA, Vertiv -> VRT); muuten jätä ticker tyhjäksi. Älä keksi tickereitä."""

TEEMA_SCHEMA = {
    "type": "object",
    "properties": {
        "arviot": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "relevantti": {"type": "boolean"},
                    "kriittisyys": {"type": "integer"},
                    "tiivistelma": {"type": "string"},
                    "yhtiot": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {"nimi": {"type": "string"}, "ticker": {"type": "string"}},
                            "required": ["nimi", "ticker"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["id", "relevantti", "kriittisyys", "tiivistelma", "yhtiot"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["arviot"],
    "additionalProperties": False,
}


def luokittele_uutiset(uutiset: list[dict]) -> dict[str, dict]:
    if not uutiset:
        return {}
    client = _client()
    arviot: dict[str, dict] = {}
    for i in range(0, len(uutiset), 20):
        era = uutiset[i:i + 20]
        rivit = json.dumps(
            [{"id": u["id"], "ticker": u["ticker"], "otsikko": u["otsikko"], "lahde": u["lahde"]} for u in era],
            ensure_ascii=False,
        )
        resp = client.messages.create(
            model=config.MALLI_LUOKITTELU, max_tokens=4000, system=LUOKITTELU_OHJE,
            messages=[{"role": "user", "content": rivit}],
            output_config={"format": {"type": "json_schema", "schema": LUOKITTELU_SCHEMA}},
        )
        teksti = next(b.text for b in resp.content if b.type == "text")
        for a in json.loads(teksti).get("arviot", []):
            arviot[a["id"]] = a
    return arviot


def koosta_some(ticker: str, nimi: str, viestit: list[dict]) -> dict:
    client = _client()
    rivit = json.dumps([{"lahde": v["lahde"], "teksti": v["teksti"]} for v in viestit[:40]], ensure_ascii=False)
    resp = client.messages.create(
        model=config.MALLI_LUOKITTELU, max_tokens=1500, system=SOME_OHJE,
        messages=[{"role": "user", "content": f"Osake: {nimi} ({ticker})\nViestit:\n{rivit}"}],
        output_config={"format": {"type": "json_schema", "schema": SOME_SCHEMA}},
    )
    teksti = next(b.text for b in resp.content if b.type == "text")
    return json.loads(teksti)


def luokittele_teemat(uutiset: list[dict]) -> dict[str, dict]:
    """Palauttaa {id: {relevantti, kriittisyys, tiivistelma, yhtiot}}."""
    if not uutiset:
        return {}
    client = _client()
    arviot: dict[str, dict] = {}
    for i in range(0, len(uutiset), 20):
        era = uutiset[i:i + 20]
        rivit = json.dumps(
            [{"id": u["id"], "teema": u["teema"], "otsikko": u["otsikko"]} for u in era],
            ensure_ascii=False,
        )
        resp = client.messages.create(
            model=config.MALLI_LUOKITTELU, max_tokens=5000, system=TEEMA_OHJE,
            messages=[{"role": "user", "content": rivit}],
            output_config={"format": {"type": "json_schema", "schema": TEEMA_SCHEMA}},
        )
        teksti = next(b.text for b in resp.content if b.type == "text")
        for a in json.loads(teksti).get("arviot", []):
            arviot[a["id"]] = a
    return arviot
