import os

# Mallivalinnat: luokittelu tehdään halvimmalla mallilla, analyysi ja suositukset fiksummalla.
# Voit vaihtaa nämä esim. arvoon "claude-opus-4-8" jos haluat parempaa laatua kalliimmalla.
MALLI_LUOKITTELU = "claude-haiku-4-5"
MALLI_ANALYYSI = "claude-sonnet-5"
MALLI_SUOSITUS = "claude-sonnet-5"

# Ilmoitustasot (kriittisyys 1-10)
HALYTYSKYNNYS = 8   # tämä ja yli -> välitön sähköposti
KOOSTEKYNNYS = 4    # tämä ja yli -> mukana iltapäiväkoosteessa

# Some-koonti tehdään vasta kun uusia viestejä on vähintään näin monta per osake
SOME_MIN_VIESTIT = 3

# Automaattinen seurantalistan hallinta (ajetaan viikoittain analyysin yhteydessä)
AUTO_SEURANTA = True        # koko toiminnon voi kytkeä pois
AUTO_LISAYS_MAINTA = 3      # teemauutisissa vähintään näin monta mainintaa -> ehdolla lisättäväksi
AUTO_MAX = 25              # seurantalistan enimmäiskoko (omat + automaattiset)
AUTO_POISTO_PAIVAT = 21    # automaattilisätty osake poistetaan, jos näin monta päivää ilman uutisia
REKISTERI_MAX = 12        # kuinka monelle yhtiölle viikoittainen näkemys tehdään (kulunhallinta)
# Omia (lahde="oma") osakkeita ei koskaan poisteta automaattisesti.

# Muistissa pidettävän datan rajat
MAX_UUTISIA_MUISTISSA = 400
MAX_NAHTYJA = 6000
MAX_TEEMAUUTISIA = 200

# Sähköposti ja valinnaiset avaimet (GitHub Secrets -> ympäristömuuttujat)
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
EMAIL_TO = os.environ.get("EMAIL_TO", GMAIL_USER)
FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "")  # valinnainen: tuloskalenteri

JUURI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(JUURI, "docs", "data")
WATCHLIST = os.path.join(JUURI, "watchlist.json")

# Tekoälyn pullonkaula-alueet ja niiden hakusanat (teemapohjainen uutishaku).
# Nimi näkyy dashboardissa; haku on Google News -kysely englanniksi.
TEEMAT = [
    {"nimi": "Laskentakapasiteetti ja sirut",
     "haku": '"AI chips" OR "GPU shortage" OR "AI accelerator" OR "data center GPU"'},
    {"nimi": "Muisti (HBM/DRAM)",
     "haku": '"HBM memory" OR "high bandwidth memory" OR "DRAM shortage AI"'},
    {"nimi": "Energia ja sähköverkot",
     "haku": '"data center power" OR "grid capacity AI" OR "electricity shortage data center"'},
    {"nimi": "Ydinvoima ja uraani",
     "haku": '"nuclear power data center" OR "uranium demand AI" OR "small modular reactor"'},
    {"nimi": "Jäähdytys",
     "haku": '"data center cooling" OR "liquid cooling AI" OR "immersion cooling"'},
    {"nimi": "Verkotus ja optiikka",
     "haku": '"optical networking AI" OR "silicon photonics" OR "co-packaged optics"'},
    {"nimi": "Kriittiset mineraalit",
     "haku": '"critical minerals" OR "rare earth AI" OR "gallium germanium supply"'},
]
