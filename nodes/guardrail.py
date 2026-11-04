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
Der Rohtext wird nur deterministisch gelesen (Namen der Empfänger), nie ans LLM gegeben.
"""

import json
import os
import re
from datetime import date

from pydantic import BaseModel, Field

from datum import MONATE
from state import MAX_VERSUCHE, BriefState, GuardrailErgebnis, Verstoss

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

_ANKOMMEN = re.compile(
    r"\b(ankommen|angekommen|eingehen|eingegangen|eintreffen|eingetroffen|nicht nur abgeschickt"
    r"|doit arriver|doivent arriver|arriver à temps|parvenir|parvienne|être reçue?"
    r"|pervenire|pervenga|deve arrivare|arrivi entro|giungere)\b",
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
    m = _ANKOMMEN.search(text)
    if m and not eingang:
        v.append(Verstoss(regel="erfundene_fakten", betrifft=betrifft,
                          detail=f"{m[0]!r}: Hier genügt die Postaufgabe am letzten Tag (SchKG Art. 32)"))

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
    update: dict = {"guardrail": ergebnis, "versuche": {"guardrail": 1}}
    bisher = (state.get("versuche") or {}).get("guardrail", 0) + 1
    if not ergebnis.bestanden and bisher >= MAX_VERSUCHE["guardrail"]:
        update["abbruch_grund"] = "guardrail_limit"
    return update
