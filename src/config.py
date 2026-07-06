import os

# Mallivalinnat: luokittelu tehdään halvimmalla mallilla, viikkoanalyysi fiksummalla.
# Voit vaihtaa nämä esim. arvoon "claude-opus-4-8" jos haluat parempaa laatua kalliimmalla.
MALLI_LUOKITTELU = "claude-haiku-4-5"
MALLI_ANALYYSI = "claude-sonnet-5"

# Ilmoitustasot (kriittisyys 1-10)
HALYTYSKYNNYS = 8   # tämä ja yli -> välitön sähköposti
KOOSTEKYNNYS = 4    # tämä ja yli -> mukana iltapäiväkoosteessa

# Some-koonti tehdään vasta kun uusia viestejä on vähintään näin monta per osake
SOME_MIN_VIESTIT = 3

# Muistissa pidettävän datan rajat
MAX_UUTISIA_MUISTISSA = 400
MAX_NAHTYJA = 6000

# Sähköposti (GitHub Secrets -> ympäristömuuttujat)
GMAIL_USER = os.environ.get("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "")
EMAIL_TO = os.environ.get("EMAIL_TO", GMAIL_USER)

JUURI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(JUURI, "docs", "data")
WATCHLIST = os.path.join(JUURI, "watchlist.json")
