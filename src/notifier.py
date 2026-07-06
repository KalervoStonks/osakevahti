"""Sähköposti-ilmoitukset Gmailin kautta (sovellussalasana)."""
import smtplib
from email.mime.text import MIMEText

from . import config


def laheta(otsikko: str, html: str) -> None:
    if not config.GMAIL_USER or not config.GMAIL_APP_PASSWORD:
        print(f"Sähköpostiasetukset puuttuvat — ohitetaan lähetys: {otsikko}")
        return
    viesti = MIMEText(html, "html", "utf-8")
    viesti["Subject"] = otsikko
    viesti["From"] = config.GMAIL_USER
    viesti["To"] = config.EMAIL_TO
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(config.GMAIL_USER, config.GMAIL_APP_PASSWORD)
        smtp.send_message(viesti)
    print(f"Sähköposti lähetetty: {otsikko}")


def _rivi(u: dict) -> str:
    linkki = f' — <a href="{u["url"]}">lähde</a>' if u.get("url") else ""
    tiivistelma = u.get("tiivistelma", "")
    return (
        f'<p style="margin:0 0 14px 0">'
        f'<strong>[{u.get("kriittisyys", "?")}/10] {u.get("ticker", "")}</strong>: '
        f'{u.get("otsikko", "")}<br>'
        f'<span style="color:#555">{tiivistelma}</span>'
        f'<span style="color:#999"> ({u.get("lahde", "")}){linkki}</span></p>'
    )


def laheta_halytys(uutiset: list[dict]) -> None:
    tickerit = ", ".join(sorted({u["ticker"] for u in uutiset}))
    runko = "".join(_rivi(u) for u in uutiset)
    html = f"<h3>Kriittisiä uutisia: {tickerit}</h3>{runko}"
    laheta(f"Osakevahti-hälytys: {tickerit}", html)


def laheta_kooste(uutiset: list[dict]) -> None:
    if not uutiset:
        return
    ryhmat: dict[str, list[dict]] = {}
    for u in sorted(uutiset, key=lambda x: -x.get("kriittisyys", 0)):
        ryhmat.setdefault(u.get("ticker", "?"), []).append(u)
    osat = []
    for ticker, lista in ryhmat.items():
        osat.append(f"<h3>{ticker}</h3>" + "".join(_rivi(u) for u in lista))
    html = "<h2>Päivän kooste</h2>" + "".join(osat)
    laheta(f"Osakevahti: päivän kooste ({len(uutiset)} nostoa)", html)
