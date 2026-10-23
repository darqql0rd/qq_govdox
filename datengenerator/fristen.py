"""Deterministische Fristberechnung für die synthetischen Testbriefe.

Regeln (sinngemäss, vor Evaluation gegen Fedlex prüfen):

SchKG (Rechtsvorschlag 10 Tage, Art. 74; Zahlung 20 Tage, Art. 69 Abs. 2 Ziff. 2):
  * Art. 31 SchKG i.V.m. Art. 142 ZPO: Frist beginnt am Tag nach der Zustellung.
    Fällt der letzte Tag auf Sa, So oder einen am Betreibungsort staatlich
    anerkannten Feiertag, endet sie am nächsten Werktag.
  * Art. 56 Ziff. 2 SchKG: Betreibungsferien 7 Tage vor bis 7 Tage nach Ostern
    und Weihnachten sowie 15.-31. Juli.
  * Art. 63 SchKG: Ferien hemmen den Fristenlauf nicht. Fällt das Fristende in die
    Ferien, wird die Frist bis zum dritten Tag nach deren Ende verlängert; Sa, So
    und staatlich anerkannte Feiertage zählen dabei nicht.

Verwaltungsverfahren (Einsprache Steuerveranlagung 30 Tage, Art. 132 DBG und
kantonales Recht): Beginn am Tag nach Zustellung, Ende an Sa/So/Feiertag ->
nächster Werktag. Kein Fristenstillstand angenommen.
"""
import datetime as dt

D = dt.date


def easter(y):
    a = y % 19; b = y // 100; c = y % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31; day = ((h + l - 7 * m + 114) % 31) + 1
    return D(y, month, day)


# Feiertage der fiktiven Kantone (an real existierende Regionen angelehnt)
def holidays(region, y):
    e = easter(y)
    t = dt.timedelta
    common = {D(y, 1, 1): "Neujahr", e + t(1): "Ostermontag", e + t(39): "Auffahrt",
              e + t(50): "Pfingstmontag", D(y, 8, 1): "Bundesfeier", D(y, 12, 25): "Weihnachten"}
    if region == "de":      # Kanton Hochwald
        common.update({D(y, 1, 2): "Berchtoldstag", e - t(2): "Karfreitag",
                       D(y, 12, 26): "Stephanstag"})
    elif region == "fr":    # Canton du Haut-Lac
        sep1 = D(y, 9, 1)
        third_sun = sep1 + t((6 - sep1.weekday()) % 7 + 14)
        common.update({D(y, 1, 2): "Berchtoldstag", e - t(2): "Vendredi saint",
                       third_sun + t(1): "Lundi du Jeûne fédéral"})
    elif region == "it":    # Cantone di Valcastello
        e60 = e + t(60)
        common.update({D(y, 1, 6): "Epifania", D(y, 3, 19): "San Giuseppe", D(y, 5, 1): "Festa del lavoro",
                       e60: "Corpus Domini", D(y, 6, 29): "SS. Pietro e Paolo", D(y, 8, 15): "Assunzione",
                       D(y, 11, 1): "Ognissanti", D(y, 12, 8): "Immacolata", D(y, 12, 26): "Santo Stefano"})
    return common


def holiday_name(d, region):
    return holidays(region, d.year).get(d)


def is_workday(d, region):
    return d.weekday() < 5 and holiday_name(d, region) is None


def why_not_workday(d, region):
    if d.weekday() == 5: return "Samstag"
    if d.weekday() == 6: return "Sonntag"
    return holiday_name(d, region)


def next_workday(d, region):
    while not is_workday(d, region):
        d += dt.timedelta(days=1)
    return d


def add_workdays(d, n, region):
    while n:
        d += dt.timedelta(days=1)
        if is_workday(d, region):
            n -= 1
    return d


def betreibungsferien(y):
    e = easter(y); t = dt.timedelta
    return [(e - t(7), e + t(7), "Oster-Betreibungsferien"),
            (D(y, 7, 15), D(y, 7, 31), "Sommer-Betreibungsferien"),
            (D(y - 1, 12, 18), D(y, 1, 1), "Weihnachts-Betreibungsferien"),
            (D(y, 12, 18), D(y + 1, 1, 1), "Weihnachts-Betreibungsferien")]


def in_ferien(d):
    for a, b, name in betreibungsferien(d.year):
        if a <= d <= b:
            return a, b, name
    return None


def wd(d):
    return ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"][d.weekday()] + " " + d.strftime("%d.%m.%Y")


def frist_schkg(zustell, tage, region):
    roh = zustell + dt.timedelta(days=tage)
    log = [f"Zustellung {wd(zustell)} + {tage} Tage = {wd(roh)}"]
    f = in_ferien(roh)
    if f:
        a, b, name = f
        end = add_workdays(b, 3, region)
        log.append(f"fällt in {name} ({a:%d.%m.%Y}-{b:%d.%m.%Y}) -> Art. 63 SchKG: "
                   f"3. Werktag nach Ferienende = {wd(end)}")
        return end, log
    if not is_workday(roh, region):
        end = next_workday(roh, region)
        log.append(f"{why_not_workday(roh, region)} -> nächster Werktag {wd(end)} (Art. 31 SchKG/Art. 142 ZPO)")
        return end, log
    log.append("Werktag, keine Verschiebung")
    return roh, log


def frist_verwaltung(zustell, tage, region):
    roh = zustell + dt.timedelta(days=tage)
    log = [f"Zustellung {wd(zustell)} + {tage} Tage = {wd(roh)}"]
    if not is_workday(roh, region):
        end = next_workday(roh, region)
        log.append(f"{why_not_workday(roh, region)} -> nächster Werktag {wd(end)}")
        return end, log
    log.append("Werktag, keine Verschiebung")
    return roh, log


def zustell_annahme(briefdatum, region):
    """Konvention, wenn kein Zustelldatum im Brief steht: Briefdatum + 2 Werktage."""
    return add_workdays(briefdatum, 2, region)


if __name__ == "__main__":
    tests = [
        ("ZB Wochenende", frist_schkg(D(2026, 10, 28), 10, "de")),
        ("ZB Weihnacht RV", frist_schkg(D(2026, 12, 14), 10, "de")),
        ("ZB Weihnacht Zahlung", frist_schkg(D(2026, 12, 14), 20, "de")),
        ("ZB Weihnacht FR RV", frist_schkg(D(2026, 12, 10), 10, "fr")),
        ("ZB Weihnacht FR Zahl", frist_schkg(D(2026, 12, 10), 20, "fr")),
        ("ZB Sommer IT RV", frist_schkg(D(2026, 7, 6), 10, "it")),
        ("ZB Sommer IT Zahl", frist_schkg(D(2026, 7, 6), 20, "it")),
        ("ZB Auffahrt IT", frist_schkg(D(2026, 5, 4), 10, "it")),
        ("ZB Auffahrt IT Z", frist_schkg(D(2026, 5, 4), 20, "it")),
        ("Steuer Weihnacht", frist_verwaltung(D(2026, 11, 25), 30, "de")),
        ("Zustell 23.11", (zustell_annahme(D(2026, 11, 23), "de"), [])),
    ]
    for n, (d, log) in tests:
        print(n, "->", wd(d), "|", " / ".join(log))
