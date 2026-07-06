# Osakevahti

Automaattinen osakeseuranta, joka pyörii ilmaiseksi GitHub Actionsissa:

- Kerää seurattavien osakkeiden uutiset (Google News, Yahoo Finance) ja sijoittajakeskustelut (StockTwits, Reddit) noin 30 minuutin välein.
- Tekoäly (Claude Haiku) arvioi jokaisen uutisen kriittisyyden asteikolla 1–10 ja tiivistää sen suomeksi.
- Kriittisistä uutisista (8+) lähtee heti sähköposti; muista merkittävistä (4–7) tulee päivittäinen kooste.
- Dashboard (GitHub Pages) näyttää uutiset, some-koonnit ja viikoittaisen AI-pullonkaula-analyysin.
- Sunnuntaisin syvempi analyysi (Claude Sonnet + web-haku) kartoittaa tekoälyn pullonkaulat liiketoiminta-alueittain, isot yhtiöt, pienet tuottopotentiaaliyhtiöt ja uudet seurantaehdokkaat.

Arvioidut käyttökulut: noin 5–10 €/kk (Anthropic API). Kaikki muu on ilmaista.

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

### Vaihe 5: Kytke GitHub Pages päälle

Repossa: Settings → Pages → kohtaan "Branch" valitse `main` ja kansioksi `/docs` → Save. Dashboardin osoite on muutaman minuutin päästä muotoa `https://KAYTTAJANIMI.github.io/osakevahti/`.

### Vaihe 6: Ensimmäinen ajo

1. Repossa: Actions-välilehti → jos GitHub kysyy, salli workflowt ("I understand... enable them").
2. Valitse vasemmalta "Uutisvahti" → "Run workflow" → Run. Ajo kestää 1–2 minuuttia.
3. Aja samalla tavalla kerran "Viikkoanalyysi", niin dashboardin Pullonkaulat-välilehti täyttyy.
4. Avaa dashboard selaimessa — uutiset ja analyysi näkyvät. Tämän jälkeen kaikki pyörii automaattisesti.

---

## Asetusten säätäminen

- Seurattavat osakkeet: muokkaa tiedostoa `watchlist.json` (ticker, yhtiön nimi hakuja varten).
- Hälytyskynnykset ja mallit: `src/config.py` (`HALYTYSKYNNYS`, `KOOSTEKYNNYS`, mallivalinnat).
- Ajoaikataulut: `.github/workflows/*.yml` (cron-rivit, ajat UTC-aikaa; Suomi on UTC+2/+3).

## Kustannusarvio

- Uutisluokittelu (Claude Haiku 4.5, 1 $ / 5 $ per miljoona tokenia): tyypillisesti 2–5 €/kk.
- Viikkoanalyysi (Claude Sonnet 5 + web-haku, enintään 8 hakua/ajo): noin 2–5 €/kk.
- GitHub, sähköposti ja tietolähteet: 0 €.

Kulutusta voi seurata osoitteessa https://console.anthropic.com (Usage). Sinne voi asettaa myös kulurajan.

## Vianetsintä

- Ei sähköposteja: tarkista salaisuuksien nimet (Vaihe 4) ja että sovellussalasana on 16-merkkinen ilman välilyöntejä.
- Actions-ajo punaisella: avaa epäonnistunut ajo ja katso lokin virheilmoitus; yleisin syy on puuttuva/virheellinen `ANTHROPIC_API_KEY` tai loppunut saldo.
- Reddit ei aina vastaa GitHubin palvelimilta (esto) — se on normaalia, muut lähteet toimivat silti.
- X/Twitter ei ole mukana, koska sen rajapinnan lukukäyttö maksaa ~200 $/kk. StockTwits ja Reddit toimivat ilmaisina korvikkeina.
