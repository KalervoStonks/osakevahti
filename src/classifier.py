"""Uutisten kriittisyysluokittelu ja some-koonnit Claude Haikulla."""
import json

import anthropic

from . import config


def _client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


LUOKITTELU_OHJE = """Olet suomalaisen yksityissijoittajan uutisvahti. Saat JSON-listan uutisotsikoita seurattavista osakkeista. Arvioi jokainen otsikko:

- kriittisyys, kokonaisluku 1-10:
  9-10 = vaikuttaa välittömästi sijoituspäätökseen: tulosvaroitus, yrityskauppa tai ostotarjous, osake- tai lainaemissio, merkittävä uusi sopimus tai tilaus, kriittinen viranomaispäätös, toimitusjohtajan äkillinen lähtö.
  6-8 = merkittävä: tulosjulkistus, ohjeistuksen muutos, iso analyytikkosuosituksen muutos, merkittävä tuotejulkistus, olennainen toimialakäänne.
  3-5 = tavanomainen yhtiö- tai toimialauutinen.
  1-2 = vähäpätöinen, spekulatiivinen listausartikkeli tai mainosmainen sisältö.
- luokka: yksi näistä: tulos, yrityskauppa, sopimus, tuote, johto, saantely, rahoitus, analyytikko, toimiala, muu
- tiivistelma: 1-2 virkettä suomeksi: mitä tapahtui ja miksi sillä on väliä sijoittajalle.

Jos otsikko ei oikeasti koske kyseistä yhtiötä, anna kriittisyys 1. Palauta arvio jokaiselle id:lle."""

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
- kriittisyys 1-10: anna yli 7 vain jos viesteissä toistuu konkreettinen, merkittävä ja uusi tieto (esim. vahvistamaton yrityskauppahuhu useasta lähteestä). Tavallinen kurssispekulaatio on korkeintaan 4."""

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


def luokittele_uutiset(uutiset: list[dict]) -> dict[str, dict]:
    """Palauttaa {id: {kriittisyys, luokka, tiivistelma}} kaikille annetuille uutisille."""
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
            model=config.MALLI_LUOKITTELU,
            max_tokens=4000,
            system=LUOKITTELU_OHJE,
            messages=[{"role": "user", "content": rivit}],
            output_config={"format": {"type": "json_schema", "schema": LUOKITTELU_SCHEMA}},
        )
        teksti = next(b.text for b in resp.content if b.type == "text")
        for a in json.loads(teksti).get("arviot", []):
            arviot[a["id"]] = a
    return arviot


def koosta_some(ticker: str, nimi: str, viestit: list[dict]) -> dict:
    """Tiivistää yhden osakkeen uudet someviestit yhdeksi koonniksi."""
    client = _client()
    rivit = json.dumps(
        [{"lahde": v["lahde"], "teksti": v["teksti"]} for v in viestit[:40]],
        ensure_ascii=False,
    )
    resp = client.messages.create(
        model=config.MALLI_LUOKITTELU,
        max_tokens=1500,
        system=SOME_OHJE,
        messages=[{"role": "user", "content": f"Osake: {nimi} ({ticker})\nViestit:\n{rivit}"}],
        output_config={"format": {"type": "json_schema", "schema": SOME_SCHEMA}},
    )
    teksti = next(b.text for b in resp.content if b.type == "text")
    return json.loads(teksti)
