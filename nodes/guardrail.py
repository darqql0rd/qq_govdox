"""Guardrail-Node (Owner: Florian): prüft Erklärung und Antwortentwurf vor der Ausgabe.

Zwei Stufen:
1. Deterministische Checks in Python (schnell, reproduzierbar, kein LLM):
   - frist_abweichung:  Datum im Text, das weder berechnet noch im Brief belegt ist;
                        falscher Wochentag neben einem Datum
   - betrag_abweichung: CHF-Betrag im Text, der nicht in der Extraktion steht
   - personendaten:     Name oder Adresse der Empfängerin / des Empfängers im Text
   - erfundene_fakten:  "muss ankommen" ohne Hinweis eingang_massgebend (SchKG Art. 32:
                        Postaufgabe genügt); Rechtsmittel, das zum Brieftyp nicht passt
   - falsche_sprache:   Text nicht in der verlangten Sprache
2. LLM-Check für das, was Regeln nicht erkennen: rechtsberatung, erfundene_fakten,
   injection_befolgt. Abschaltbar mit GUARDRAIL_LLM=0 in .env (z. B. für schnelle Tests).

Bei Verstoss springt der Graph zurück (zurueck_zu), höchstens MAX_VERSUCHE["guardrail"] Mal.
Danach ersetzt nodes/sichere_ausgabe.py die beanstandeten Texte (Fallback ohne LLM).
Der Rohtext wird nur deterministisch gelesen (Namen der Empfänger), nie ans LLM gegeben.
"""

import json
import os
import re
from datetime import date

from pydantic import BaseModel, Field

from datum import MONATE
from state import BriefState, GuardrailErgebnis, Verstoss

# ---------------------------------------------------------------------------
# Hilfsfunktionen: Daten und Beträge in Texten finden
# ---------------------------------------------------------------------------

_DATUM_ZAHL = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})\b")
_DATUM_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DATUM_WORT = re.compile(
    r"\b(\d{1,2})\s*(?:\.|er|°|º)?\s+([A-Za-zÄÖÜäöüéèûàô]+)\s+(\d{4})\b"
)

WOCHENTAGE = {
    # Python: Montag = 0
    "montag": 0, "dienstag": 1, "mittwoch": 2, "donnerstag": 3, "freitag": 4,
    "samstag": 5, "sonntag": 6,
    "lundi": 0, "mardi": 1, "mercredi": 2, "jeudi": 3, "vendredi": 4, "samedi": 5,
    "dimanche": 6,
    "lunedì": 0, "martedì": 1, "mercoledì": 2, "giovedì": 3, "venerdì": 4, "sabato": 5,
    "domenica": 6,
}


def _jahr(t: str) -> int:
    j = int(t)
    return j + 2000 if j < 100 else j


def daten_im_text(text: str) -> list[tuple[date, int, int]]:
    """Alle Daten im Text als (Datum, Start, Ende). Ungültige Daten werden übersprungen."""
    gefunden = []
    for m in _DATUM_ZAHL.finditer(text):
        try:
            gefunden.append((date(_jahr(m[3]), int(m[2]), int(m[1])), m.start(), m.end()))
        except ValueError:
            pass
    for m in _DATUM_ISO.finditer(text):
        try:
            gefunden.append((date(int(m[1]), int(m[2]), int(m[3])), m.start(), m.end()))
        except ValueError:
            pass
    for m in _DATUM_WORT.finditer(text):
        monat = MONATE.get(m[2].lower())
        if monat:
            try:
                gefunden.append((date(int(m[3]), monat, int(m[1])), m.start(), m.end()))
            except ValueError:
                pass
    return gefunden


# Beträge: mit Rappen (1'915.90, 1 915,90, 6540.30) oder ganze Zahl mit Währung (400 Franken)
_BETRAG_RAPPEN = re.compile(r"(?<![\d.,'’])(\d{1,3}(?:['’  ]\d{3})+|\d+)[.,](\d{2})(?![\d])")
_BETRAG_GANZ = re.compile(
    r"(?:(?:CHF|Fr\.)\s*(\d{1,3}(?:['’  ]\d{3})+|\d+)(?:\.[-–]|(?![.,'’\u202f ]?\d)))"
    r"|(?:(?<![\d.,'’])(\d{1,3}(?:['’  ]\d{3})+|\d+)(?:\.[-–])?\s*"
    r"(?:CHF|Franken|francs|franchi)\b)",
    re.IGNORECASE,
)


def _zahl(ganz: str, rappen: str | None = None) -> float:
    ganz = re.sub(r"['’  ]", "", ganz)
    return round(float(f"{ganz}.{rappen or '00'}"), 2)


def betraege_im_text(text: str) -> list[float]:
    # Daten zuerst ausblenden, sonst wird "09.11.2026" als Betrag 9.11 gelesen
    for _, start, ende in daten_im_text(text):
        text = text[:start] + " " * (ende - start) + text[ende:]
    text = re.sub(r"\b\d{1,2}\.\d{1,2}\.(?!\d)", lambda m: " " * len(m[0]), text)  # "30.11."
    werte = [_zahl(m[1], m[2]) for m in _BETRAG_RAPPEN.finditer(text)]
    for m in _BETRAG_GANZ.finditer(text):
        werte.append(_zahl(m[1] or m[2]))
    return werte


def _alle_werte(objekt) -> list:
    """Alle Blätter eines verschachtelten dict/list (aus model_dump)."""
    if isinstance(objekt, dict):
        return [w for v in objekt.values() for w in _alle_werte(v)]
    if isinstance(objekt, list):
        return [w for v in objekt for w in _alle_werte(v)]
    return [objekt]


def _dump(objekt):
    return objekt.model_dump(mode="json") if hasattr(objekt, "model_dump") else objekt


# ---------------------------------------------------------------------------
# Was ist belegt? (Daten, Beträge, Personen)
# ---------------------------------------------------------------------------

def belegte_daten(state: BriefState) -> set[date]:
    texte = [str(w) for w in _alle_werte(_dump(state.get("extraktion")))]
    texte += [str(w) for f in state.get("fristen", []) for w in _alle_werte(_dump(f))]
    if state.get("zustelldatum"):
        texte.append(str(state["zustelldatum"]))
    return {d for t in texte for d, _, _ in daten_im_text(t)}


def belegte_betraege(state: BriefState) -> set[float]:
    werte: set[float] = set()
    for w in _alle_werte(_dump(state.get("extraktion"))):
        if isinstance(w, (int, float)) and not isinstance(w, bool):
            werte.add(round(abs(float(w)), 2))
        elif isinstance(w, str):
            werte.update(abs(b) for b in betraege_im_text(w))
            werte.update(_zahl(z) for z in re.findall(r"\d{1,3}(?:['’]\d{3})+", w))
    # Summe der Posten ist belegt, auch wenn das LLM den Hauptbetrag falsch addiert hat
    ex = _dump(state.get("extraktion")) or {}
    posten = [p.get("betrag_chf") for p in ex.get("posten") or [] if p.get("betrag_chf") is not None]
    if posten:
        werte.add(round(abs(sum(posten)), 2))
    return werte


_ANREDEN = re.compile(
    r"^(Herr und Frau|Herr|Frau|Familie|Monsieur et Madame|Madame|Monsieur|Famille|"
    r"Signori|Signora|Signor)\b"
)
_NAME = re.compile(r"^[A-ZÄÖÜ][a-zäöüéèàìç]+(?: (?:und|et|e) [A-ZÄÖÜ][a-zäöüéèàìç]+)? [A-ZÄÖÜ][a-zäöüéèàìç]+$")
_STRASSE = re.compile(
    r"\b(?:[A-ZÄÖÜ][\wäöüéèàì-]*(?:strasse|weg|gasse|platz|allee|rain|ring|halde)"
    r"|(?:Rue|Chemin|Avenue|Route|Place|Via|Strada|Piazza|Vicolo|Viale)\s+[\w' -]+?)\s+\d+[a-z]?\b"
)


def personendaten_aus_rohtext(state: BriefState) -> set[str]:
    """Nachnamen und Strasse der Empfängerin / des Empfängers aus dem Adressblock."""
    rohtext = state.get("rohtext") or ""
    belegt = " ".join(str(w) for w in _alle_werte(_dump(state.get("extraktion"))))
    zeilen = [z.strip() for z in rohtext.splitlines() if z.strip()]
    treffer: set[str] = set()
    for i, zeile in enumerate(zeilen):
        if not _ANREDEN.match(zeile):
            continue
        # Adressblock: die nächsten Zeilen, zweispaltige Layouts in Stücke teilen
        for z in zeilen[i:i + 4]:
            for stueck in re.split(r"\s{3,}", z):
                stueck = stueck.strip()
                if _NAME.match(stueck):
                    nachname = stueck.split()[-1]
                    if nachname not in belegt:
                        treffer.add(nachname)
                strasse = _STRASSE.search(stueck)
                if strasse and strasse[0] not in belegt:
                    treffer.add(strasse[0])
        break
    return treffer


# ---------------------------------------------------------------------------
# Deterministische Checks
# ---------------------------------------------------------------------------

# "Ankommen" wird pro Satz geprüft (Lauf 09.11.: "Der Brief ist in den Betreibungsferien
# angekommen" ist richtig, "... so, dass er bis dahin dort ankommt" ist falsch):
# - Grundform/Präsens (ankommt, eintrifft, parvienne ...) zusammen mit Modalverb oder Fristwort
# - Partizip (angekommen, parvenu ...) nur zusammen mit Modalverb ("muss angekommen sein")
# Punkte in 09.11.2026 trennen keine Sätze. Ein Punkt NACH einem Datum schon, wenn ein neuer Satz
# folgt (Lauf 16.11., Brief 06: "... avant le 06.01.2027. Comme le brief est arrivé ..." wurde
# sonst ein Satz, und "doit" + "arrivé" ergab einen Fehlalarm).
_SATZENDE = re.compile(r"(?<!\d)[.!?](?!\d)|(?<=\d)\.(?=\s+[A-ZÄÖÜÀÂÉÈÊÎÔÙÛÇ])|\n")
_ANKOMMEN = re.compile(
    r"\b(ankommen|ankommt|eingehen|eingeht|eintreffen|eintrifft|nicht nur abgeschickt"
    r"|arriver|arrive|arrivent|parvenir|parvienne|parvient|être reçue?"
    r"|arrivare|arrivi|arriva|pervenire|pervenga|perviene|giungere|giunga)\b",
    re.IGNORECASE,
)
_ANGEKOMMEN = re.compile(
    r"\b(angekommen|eingegangen|eingetroffen|arrivée?s?|parvenue?s?"
    r"|arrivat[oaie]|pervenut[oaie]|giunt[oaie])\b",
    re.IGNORECASE,
)
_MODAL = re.compile(r"\b(muss|müssen|doit|doivent|deve|devono)\b", re.IGNORECASE)
_FRISTWORT = re.compile(
    r"\b(bis|spätestens|rechtzeitig|avant|au plus tard|à temps|entro|in tempo)\b", re.IGNORECASE)


def _saetze(text: str) -> list[str]:
    return [s for s in _SATZENDE.split(text) if s and s.strip()]


def _ankommen_im_satz(text: str) -> str | None:
    """Erste Formulierung "muss ankommen" (oder gleichbedeutend), sonst None."""
    for satz in _saetze(text):
        modal, frist = _MODAL.search(satz), _FRISTWORT.search(satz)
        m = _ANKOMMEN.search(satz)
        if m and (modal or frist):
            return m[0]
        m = _ANGEKOMMEN.search(satz)
        if m and modal:
            return m[0]
        m = _MUSS_ERHALTEN.search(satz)
        if m:
            return m[0]
    return None


# Rechtsvorschlag/Einsprache = Forderung bestreiten, kein Weg, um nicht zu zahlen (Lauf 09.11.).
# Nur im selben Satz wie das Rechtsmittel: "Wenn Sie nicht zahlen können, wenden Sie sich an
# eine Schuldenberatung" bleibt erlaubt.
_NICHT_ZAHLEN_WOLLEN = re.compile(
    r"\bnicht\s+(be)?zahlen\s+(wollen|möchten|können|will|möchte|kann)\b"
    r"|\b(wollen|möchten|können)\s+(Sie\s+)?nicht\s+(be)?zahlen\b"
    r"|\bne\s+(voulez|souhaitez|pouvez|voulez-vous)\s+pas\s+payer\b"
    r"|\bnon\s+(vuole|vuol|desidera|può|volete|potete)\s+pagare\b",
    re.IGNORECASE,
)
_RECHTSMITTEL = re.compile(
    r"\b(Rechtsvorschlag|Einsprache|opposition|réclamation|opposizione|reclamo)\b", re.IGNORECASE)

# Beim Zahlungsbefehl ist die Zahlung keine feststehende Pflicht: Mit dem Rechtsvorschlag kann
# die Person die Forderung bestreiten. Gespeicherte Fälle 09/10: "Lei deve pagare CHF 1'030.30."
# Der LLM-Check meldete das in 3 Läufen nur 1 von 9 Mal. Erlaubt bleiben Verneinungen ("Sie
# müssen nichts bezahlen") und Bedingungen ("Wenn Sie anerkennen, müssen Sie ... bezahlen",
# "deve pagare ..., se intende pagare", "Ein Gericht entscheidet, ob Sie zahlen müssen").
# Bei der Steuer gilt die Regel nicht.
_PFLICHT = re.compile(r"\b(müssen|muss|verpflichtet|devez|doit|doivent|dovete|deve|tenut[oa])\b",
                      re.IGNORECASE)
_ZAHLEN = re.compile(r"\b((be)?zahlen|payer|verser|pagare|versare)\b", re.IGNORECASE)
_PFLICHT_AUSNAHME = re.compile(
    r"\b(nichts|nicht|kein\w*|pas|rien|non|niente|nulla"
    r"|wenn|falls|sofern|sobald|ob|si|s'il|se|qualora)\b", re.IGNORECASE)


def _zahlung_als_pflicht(text: str) -> str | None:
    for satz in _saetze(text):
        p, z = _PFLICHT.search(satz), _ZAHLEN.search(satz)
        if p and z and not _PFLICHT_AUSNAHME.search(satz):
            return satz.strip()[:80]
    return None


# Fachbegriff für den Rechtsvorschlag (wie FACHBEGRIFF in nodes/antwort.py): IT "opposizione".
# Gespeicherter Fall 08: "deve presentare il rigetto (Rechtsvorschlag)". "Rigetto
# dell'opposizione" ist die Rechtsöffnung und bleibt erlaubt.
_FALSCHER_FACHBEGRIFF = re.compile(r"\brigett[oi]\b(?!\s+dell'opposizione)", re.IGNORECASE)


# Beim Zahlungsbefehl fordert der Gläubiger, das Betreibungsamt stellt nur zu (Lauf 09.11.:
# "Das Betreibungsamt Talwil verlangt im Auftrag der ... eine Zahlung"). Erlaubt bleiben
# "Die Firma verlangt über das Betreibungsamt ..." und "Das Betreibungsamt fordert Sie auf, ...".
_AMT_FORDERT = re.compile(
    r"\b(?P<amt>Betreibungsamt\w*|office des poursuites|ufficio d'esecuzione"
    r"|ufficio di esecuzione|ufficio esecuzioni)\b(?:[^.\n]|\.(?=\d)){0,40}?"
    r"\b(?P<verb>fordert|verlangt|exige|réclame|esige|pretende)\b",
    re.IGNORECASE,
)
_AMT_NICHT_SUBJEKT = {"beim", "über", "vom", "an", "dem", "zum", "durch", "via", "par",
                      "tramite", "dall", "all", "presso", "auprès", "de", "à"}


def _amt_als_glaeubiger(text: str) -> str | None:
    for satz in _saetze(text):
        for m in _AMT_FORDERT.finditer(satz):
            vor = re.findall(r"[\w']+", satz[:m.start("amt")].lower())[-2:]  # z. B. "über das"
            if any(w.split("'")[0] in _AMT_NICHT_SUBJEKT for w in vor):
                continue  # "über das Betreibungsamt", "par l'office" -> Amt ist nicht Subjekt
            if m["verb"].lower() == "fordert" and re.search(r"\bfordert\b.*\bauf\b", satz[m.start("verb"):]):
                continue  # "fordert Sie auf, ... zu zahlen" = Zahlungsbefehl, richtig
            return m[0].strip()
    return None
# Gleiche Bedeutung wie "ankommen", aber mit einem Wort, das allein harmlos ist
# ("Sie haben einen Zahlungsbefehl erhalten"). Deshalb nur zusammen mit "muss/doit/deve"
# im selben Satz (Punkte in Daten wie 09.11.2026 beenden den Satz nicht).
# Lauf 06.11., Brief 01: "Das Betreibungsamt muss Ihren Rechtsvorschlag bis zum 09.11.2026 erhalten."
_MUSS_ERHALTEN = re.compile(
    r"\b(muss|müssen)\b(?:[^.\n]|\.(?=\d)){0,80}\b(erhalten|bekommen|vorliegen)\b"
    r"|\b(doit|doivent)\b(?:[^.\n]|\.(?=\d)){0,60}\b(recevoir|reçue?s?)\b"
    r"|\b(deve|devono)\b(?:[^.\n]|\.(?=\d)){0,60}\b(ricevere|ricevut[oaie])\b",
    re.IGNORECASE,
)
# "Annahme" ist nur richtig, wenn das Zustelldatum geschätzt ist. Kommt es aus dem Brief oder
# von der Person, hat das LLM die Regel übertragen (6 von 45 gespeicherten Fällen, Live-Test 09.11.).
_ANNAHME = re.compile(
    r"\b(Annahme|angenommen|geschätzt|geschaetzt|Schätzung"
    r"|estimation|estimée?s?|supposition|supposée?s?|hypothèse|présumée?s?"
    r"|stima|stimat[oaie]|ipotesi|supposizione|presunt[oaie])\b",
    re.IGNORECASE,
)
_RECHTSVORSCHLAG = re.compile(r"\b(Rechtsvorschlag|opposition|opposizione)\b", re.IGNORECASE)
_EINSPRACHE = re.compile(r"\b(Einsprache|réclamation|reclamo)\b", re.IGNORECASE)

_STOPPWOERTER = {
    "de": {"und", "der", "die", "das", "sie", "ist", "nicht", "mit", "bis", "den", "ein", "eine"},
    "fr": {"et", "le", "la", "les", "vous", "est", "pas", "avec", "une", "des", "du", "pour"},
    "it": {"e", "il", "la", "che", "lei", "è", "non", "con", "una", "dei", "del", "per"},
}


def _sprache_von(text: str) -> str | None:
    woerter = re.findall(r"[a-zäöüéèàìòùç]+", text.lower())
    if len(woerter) < 15:
        return None
    zaehler = {s: sum(w in sw for w in woerter) for s, sw in _STOPPWOERTER.items()}
    return max(zaehler, key=zaehler.get)


def pruefe_text(text: str, betrifft: str, state: BriefState, verlangte_sprache: str | None,
                ist_entwurf: bool = False) -> list[Verstoss]:
    v: list[Verstoss] = []
    brieftyp = state.get("brieftyp")

    # Fristen und Daten
    erlaubt = belegte_daten(state)
    for d, start, ende in daten_im_text(text):
        if d not in erlaubt:
            v.append(Verstoss(regel="frist_abweichung", betrifft=betrifft,
                              detail=f"Datum {text[start:ende]!r} ist weder berechnet noch im Brief belegt"))
        # Wochentag direkt vor dem Datum ("Montag, 9.11.2026")
        vorher = text[max(0, start - 25):start].lower()
        for name, nummer in WOCHENTAGE.items():
            if re.search(rf"\b{name}\b[\s,]*(den |le |il )?$", vorher) and d.weekday() != nummer:
                v.append(Verstoss(regel="frist_abweichung", betrifft=betrifft,
                                  detail=f"Wochentag {name!r} passt nicht zu {text[start:ende]}"))

    # Beträge
    erlaubt_b = belegte_betraege(state)
    for b in betraege_im_text(text):
        if b not in erlaubt_b:
            v.append(Verstoss(regel="betrag_abweichung", betrifft=betrifft,
                              detail=f"Betrag {b:.2f} steht nicht in der Extraktion"))

    # Personendaten (im Entwurf sind Platzhalter wie [Name] erlaubt)
    for teil in personendaten_aus_rohtext(state):
        if re.search(rf"\b{re.escape(teil)}\b", text):
            v.append(Verstoss(regel="personendaten", betrifft=betrifft,
                              detail=f"Personendaten im Text: {teil!r}"))

    # "Muss ankommen" nur, wenn der Eingang massgebend ist (Krankenkasse)
    eingang = any("eingang_massgebend" in (_dump(f).get("hinweise") or [])
                  for f in state.get("fristen", []))
    wort = _ankommen_im_satz(text)
    if wort and not eingang:
        v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                          detail=f"{wort!r}: Hier genügt die Postaufgabe am letzten Tag (SchKG Art. 32)"))

    # Rechtsmittel als Weg, um nicht zu zahlen
    for satz in _saetze(text):
        m = _NICHT_ZAHLEN_WOLLEN.search(satz)
        if m and _RECHTSMITTEL.search(satz):
            v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                              detail=f"{m[0]!r}: Rechtsvorschlag/Einsprache heisst, die Forderung "
                                     "zu bestreiten, nicht, nicht zahlen zu wollen"))
            break

    # Zahlung als feststehende Pflicht und falscher Fachbegriff (nur Zahlungsbefehl)
    if brieftyp == "zahlungsbefehl":
        satz = _zahlung_als_pflicht(text)
        if satz:
            v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                              detail=f"{satz!r}: Beim Zahlungsbefehl ist die Zahlung keine "
                                     "feststehende Pflicht (Rechtsvorschlag möglich)"))
        m = _FALSCHER_FACHBEGRIFF.search(text)
        if m:
            v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                              detail=f"{m[0]!r}: Der Rechtsvorschlag heisst auf Italienisch "
                                     "'opposizione'"))

    # Betreibungsamt als Gläubiger
    if brieftyp == "zahlungsbefehl":
        treffer = _amt_als_glaeubiger(text)
        if treffer:
            v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                              detail=f"{treffer!r}: Es fordert der Gläubiger, das Betreibungsamt "
                                     "stellt nur zu"))

    # "Annahme" nur, wenn das Zustelldatum wirklich geschätzt ist
    geschaetzt = state.get("zustelldatum_quelle") == "geschaetzt" or any(
        "zustelldatum_geschaetzt" in (_dump(f).get("hinweise") or [])
        for f in state.get("fristen", []))
    m = _ANNAHME.search(text)
    if m and not geschaetzt:
        quelle = {"brief": "steht im Brief", "nutzer": "hat die Person angegeben"}.get(
            state.get("zustelldatum_quelle"), "ist nicht geschätzt")
        v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                          detail=f"{m[0]!r}: Das Zustelldatum {quelle}, es ist keine Annahme"))

    # Rechtsmittel passend zum Brieftyp
    m = _RECHTSVORSCHLAG.search(text)
    if m and brieftyp not in ("zahlungsbefehl", "steuerveranlagung"):
        v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                          detail=f"{m[0]!r} passt nicht zum Brieftyp {brieftyp}"))
    if m and brieftyp == "steuerveranlagung" and m[0].lower() == "rechtsvorschlag":
        v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                          detail="Rechtsvorschlag gibt es nur gegen einen Zahlungsbefehl"))
    m = _EINSPRACHE.search(text)
    if m and brieftyp in ("zahlungsbefehl", "mahnung", "krankenkasse_praemie"):
        v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                          detail=f"{m[0]!r} passt nicht zum Brieftyp {brieftyp}"))

    # Sprache
    if verlangte_sprache and not ist_entwurf:
        erkannt = _sprache_von(text)
        if erkannt and erkannt != verlangte_sprache:
            v.append(Verstoss(regel="falsche_sprache", betrifft=betrifft,
                              detail=f"Text ist {erkannt}, verlangt war {verlangte_sprache}"))
    return v


def deterministische_checks(state: BriefState) -> list[Verstoss]:
    verstoesse: list[Verstoss] = []
    sprache = state.get("nutzersprache") or state.get("briefsprache")
    erkl = state.get("erklaerung")
    if erkl:
        e = _dump(erkl)
        text = e["text"] + "\n" + "\n".join(e.get("naechste_schritte", []))
        verstoesse += pruefe_text(text, "erklaerung", state, sprache)
    entwurf = state.get("antwortentwurf")
    if entwurf:
        a = _dump(entwurf)
        verstoesse += pruefe_text(a["betreff"] + "\n" + a["text"], "antwortentwurf", state,
                                  state.get("antwortsprache"), ist_entwurf=True)
    # doppelte Meldungen entfernen
    eindeutig = {(x.regel, x.betrifft, x.detail): x for x in verstoesse}
    return list(eindeutig.values())


# ---------------------------------------------------------------------------
# LLM-Check
# ---------------------------------------------------------------------------

class LlmVerstoss(BaseModel):
    regel: str = Field(description="'rechtsberatung', 'erfundene_fakten' oder 'injection_befolgt'")
    betrifft: str = Field(description="'erklaerung' oder 'antwortentwurf'")
    detail: str = Field(description="Kurze Begründung mit dem betroffenen Satz")
    eindeutig: bool = Field(
        description="true nur bei einem klaren Verstoss; bei Grenzfällen oder Zweifeln false"
    )


class LlmPruefung(BaseModel):
    verstoesse: list[LlmVerstoss] = Field(default_factory=list)


def llm_check(state: BriefState) -> list[Verstoss]:
    from langchain_core.messages import HumanMessage, SystemMessage

    from llm import strukturiert
    from prompts import GUARDRAIL_SYSTEM

    fakten = {
        "brieftyp": state.get("brieftyp"),
        "injection_verdacht": state.get("injection_verdacht", False),
        # Zustelldatum steht nicht in der Extraktion, wenn die Person es angegeben hat
        "zustelldatum": str(state.get("zustelldatum")) if state.get("zustelldatum") else None,
        "zustelldatum_quelle": state.get("zustelldatum_quelle"),
        "extraktion": _dump(state.get("extraktion")),
        "fristen": [_dump(f) for f in state.get("fristen", [])],
        "erklaerung": _dump(state.get("erklaerung")),
        "antwortentwurf": _dump(state.get("antwortentwurf")),
    }
    ergebnis: LlmPruefung = strukturiert(LlmPruefung).invoke([
        SystemMessage(GUARDRAIL_SYSTEM),
        HumanMessage(json.dumps(fakten, ensure_ascii=False, default=str)),
    ])
    erlaubt = {"rechtsberatung", "erfundene_fakten", "injection_befolgt"}
    return [Verstoss(regel=x.regel, betrifft=x.betrifft, detail=f"[LLM] {x.detail}")
            for x in ergebnis.verstoesse
            # Grenzfälle verwerfen: lieber ein Verstoss zu wenig als ständige Fehlalarme
            if x.eindeutig and x.regel in erlaubt and x.betrifft in ("erklaerung", "antwortentwurf")]


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

def pruefe(state: BriefState, mit_llm: bool | None = None) -> GuardrailErgebnis:
    """Prüft einen State und gibt das Ergebnis zurück, ohne den State zu ändern (für Tests)."""
    if mit_llm is None:
        mit_llm = os.getenv("GUARDRAIL_LLM", "1") != "0"
    verstoesse = deterministische_checks(state)
    if mit_llm:
        verstoesse += llm_check(state)
    betroffen = {x.betrifft for x in verstoesse}
    zurueck = None
    if betroffen == {"erklaerung"}:
        zurueck = "erklaerung"
    elif betroffen == {"antwortentwurf"}:
        zurueck = "antwort"
    elif betroffen:
        zurueck = "beide"
    return GuardrailErgebnis(bestanden=not verstoesse, verstoesse=verstoesse, zurueck_zu=zurueck)


def guardrail(state: BriefState) -> dict:
    ergebnis = pruefe(state)
    # Am Limit entscheidet graph.nach_guardrail: weiter zu sichere_ausgabe (Fallback)
    return {"guardrail": ergebnis, "versuche": {"guardrail": 1}}
