# Osakevahti

Automaattinen osakeseuranta, joka pyörii ilmaiseksi GitHub Actionsissa:

- Kerää seurattavien osakkeiden uutiset (Google News, Yahoo Finance), viralliset pörssitiedotteet (SEC ja ASX), sijoittajakeskustelut (StockTwits, Reddit) ja kurssit noin 30 minuutin välein.
- Tekoäly (Claude Haiku) arvioi jokaisen havainnon kriittisyyden asteikolla 1–10 ja tiivistää sen suomeksi.
- Kriittisistä uutisista (8+) lähtee heti sähköposti; muista merkittävistä (4–7) tulee päivittäinen kooste.
- Teemahaku kartoittaa päivittäin koko tekoälyn pullonkaula-uutisvirran (sirut, muisti, energia, ydinvoima, jäähdytys, verkotus, kriittiset mineraalit) ja nostaa esiin uusia yhtiöitä, joita et vielä seuraa.
- Dashboard (GitHub Pages) näyttää uutiset, teemat, kurssikontekstin, viikkoanalyysin ja tekoälyn sijoitusnäkemykset.
- Sunnuntaisin syvempi analyysi (Claude Sonnet + web-haku) kartoittaa pullonkaulat liiketoiminta-alueittain ja muodostaa jokaisesta yhtiöstä itsenäisen sijoitusnäkemyksen (osta/lisää/pidä/vähennä/myy), jossa tunnusluvut tulkitaan yhtiötyypin mukaan.
- Seurantalista päivittyy automaattisesti: uusia yhtiöitä lisätään, kun ne nousevat esiin analyysissä ja uutisissa, ja hiljentyneet automaattilisätyt yhtiöt poistetaan. Omia osakkeitasi (`lahde: "oma"`) ei koskaan poisteta, ja jokaisesta muutoksesta tulee sähköposti.

Arvioidut käyttökulut: noin 8–18 €/kk (Anthropic API). Kaikki muu on ilmaista. Kuluja voi pienentää harventamalla teema- ja suositusajoja tai vaihtamalla halvempaan malliin.

> **Sijoitusnäkemykset eivät ole sijoitusneuvontaa.** Ne ovat tekoälyn julkisesta datasta tekemiä päätelmiä ja voivat olla virheellisiä. Vastuu päätöksistä on sinulla.

---

## Käyttöönotto vaihe vaiheelta

Tarvitset kolme asiaa: GitHub-tilin, Anthropic API-avaimen ja Gmailin sovellussalasanan. Aikaa kuluu noin 20–30 minuuttia.

### Vaihe 1: Luo GitHub-tili ja repo

1. Mene osoitteeseen https://github.com/signup ja luo tili (sähköposti + salasana).
2. Kirjautuneena paina oikean yläkulman +-nappia → "New repository".
3. Nimeä repo esim. `osakevahti`. Valitse "Public" (julkinen repo saa GitHub Pagesin ja rajattomat Actions-minuutit ilmaiseksi — älä laita repoon mitään, mitä et halua julkiseksi, esim. omistusmääriä).
4. Paina "Create repository". Tiedostojen vienti repoon tehdään yhdessä Clauden kanssa (tai itse GitHub Desktop -ohjelmalla).

### Vaihe 2: Luo Anthropic API-avain

1. Mene osoitteeseen https://console.anthropic.com ja luo tili.
2. Valitse vasemmasta valikosta "Billing" ja lisää maksukortti sekä pieni saldo, esim. 10 $. Käyttö laskutetaan vain toteutuneesta kulutuksesta.
3. Valitse "API Keys" → "Create Key". Kopioi avain heti talteen (sitä ei näytetä uudelleen). Avain alkaa `sk-ant-`.

### Vaihe 3: Luo Gmailin sovellussalasana

1. Mene osoitteeseen https://myaccount.google.com/security ja varmista, että kaksivaiheinen vahvistus (2-Step Verification) on päällä — sovellussalasanat vaativat sen.
2. Mene osoitteeseen https://myaccount.google.com/apppasswords
3. Anna nimeksi esim. "Osakevahti" ja paina "Create". Saat 16-merkkisen salasanan — kopioi se talteen.

### Vaihe 4: Tallenna salaisuudet GitHubiin

Repossa: Settings → Secrets and variables → Actions → "New repository secret". Luo kolme salaisuutta:

| Nimi | Arvo |
|---|---|
| `ANTHROPIC_API_KEY` | Vaiheen 2 API-avain |
| `GMAIL_USER` | Gmail-osoitteesi |
| `GMAIL_APP_PASSWORD` | Vaiheen 3 sovellussalasana |
| `FINNHUB_API_KEY` | Valinnainen. Ilmainen avain osoitteesta https://finnhub.io lisää tuloskalenterin (näet tulospäivät etukäteen). Voit jättää tämän pois — kaikki muu toimii ilman. |

### Vaihe 5: Kytke GitHub Pages päälle

Repossa: Settings → Pages → kohtaan "Branch" valitse `main` ja kansioksi `/docs` → Save. Dashboardin osoite on muutaman minuutin päästä muotoa `https://KAYTTAJANIMI.github.io/osakevahti/`.

### Vaihe 6: Ensimmäinen ajo

1. Repossa: Actions-välilehti → jos GitHub kysyy, salli workflowt ("I understand... enable them").
2. Valitse vasemmalta "Uutisvahti" → "Run workflow" → Run. Ajo kestää 1–2 minuuttia (uutiset, tiedotteet, kurssit).
3. Aja samalla tavalla "Teemat" (teemauutiset ja etusivun prosentit) ja "Viikkoanalyysi" (pullonkaula-analyysi ja sijoitusnäkemykset). Viikkoanalyysi kestää muutaman minuutin.
4. Avaa dashboard selaimessa — uutiset, teemat ja näkemykset näkyvät. Tämän jälkeen kaikki pyörii automaattisesti.

---

## Asetusten säätäminen

- Seurattavat osakkeet: muokkaa tiedostoa `watchlist.json`. Merkitse omat osakkeesi `"lahde": "oma"`, niin niitä ei koskaan poisteta automaattisesti. Automaattisesti lisätyt saavat merkinnän `"lahde": "auto"`.
- Hälytyskynnykset ja mallit: `src/config.py` (`HALYTYSKYNNYS`, `KOOSTEKYNNYS`, mallivalinnat).
- Automaattinen seuranta: `src/config.py` (`AUTO_SEURANTA` päälle/pois, `AUTO_MAX` listan enimmäiskoko, `AUTO_POISTO_PAIVAT` hiljaisuusraja poistolle, `AUTO_LISAYS_MAINTA` lisäyskynnys).
- Ajoaikataulut: `.github/workflows/*.yml` (cron-rivit, ajat UTC-aikaa; Suomi on UTC+2/+3).

## Kustannusarvio

- Uutis- ja teemaluokittelu (Claude Haiku 4.5): tyypillisesti 3–7 €/kk.
- Viikkoanalyysi + sijoitusnäkemykset (Claude Sonnet 5 + web-haku): noin 3–8 €/kk.
- GitHub, sähköposti ja tietolähteet: 0 €.

Kulut kasvavat lähinnä seurattavien osakkeiden ja teema-ajojen määrästä. Halutessasi voit harventaa teema-ajoja (`.github/workflows/teemat.yml`) tai vaihtaa mallit halvempaan (`src/config.py`). Kulutusta voi seurata osoitteessa https://console.anthropic.com (Usage), jonne voi asettaa myös kulurajan.

## Vianetsintä

- Ei sähköposteja: tarkista salaisuuksien nimet (Vaihe 4) ja että sovellussalasana on 16-merkkinen ilman välilyöntejä.
- Actions-ajo punaisella: avaa epäonnistunut ajo ja katso lokin virheilmoitus; yleisin syy on puuttuva/virheellinen `ANTHROPIC_API_KEY` tai loppunut saldo.
- Reddit ei aina vastaa GitHubin palvelimilta (esto) — se on normaalia, muut lähteet toimivat silti.
- X/Twitter ei ole mukana, koska sen rajapinnan lukukäyttö maksaa ~200 $/kk. StockTwits ja Reddit toimivat ilmaisina korvikkeina.
