"""Fallback-Node (Owner: Florian): sichere Ausgabe, wenn der Guardrail am Limit ist.

Läuft nur, wenn der Guardrail nach MAX_VERSUCHE["guardrail"] Versuchen noch Verstösse findet.
Ersetzt wird nur der Text, den der Guardrail beanstandet hat (Verstoss.betrifft):

- Erklärung beanstandet  -> feste Vorlage aus Python, ohne LLM: Brieftyp, Absender, Betrag,
                            Zustelldatum und die Fristen aus dem Fristenrechner. Die Fristen
                            kommen nicht vom LLM und sind das Wichtigste für die Person.
- Antwortentwurf beanstandet -> weglassen. Einen Entwurf mit Fehler würde die Person so
                            abschicken, und für einen Brief gibt es keine sinnvolle Vorlage.

Die verworfenen Texte bleiben in erklaerung_verworfen / antwortentwurf_verworfen (für
LangSmith und die Auswertung), werden aber nicht ausgegeben. Danach geht es normal weiter
zur Bestätigung und zum Kalender.
"""

from prompts import HINWEIS_PROTOTYP
from state import BriefState, Erklaerung

BRIEFTYP = {
    "zahlungsbefehl": {"de": "Zahlungsbefehl", "fr": "Commandement de payer",
                       "it": "Precetto esecutivo"},
    "steuerveranlagung": {"de": "Steuerveranlagung", "fr": "Décision de taxation",
                          "it": "Decisione di tassazione"},
    "krankenkasse_praemie": {"de": "Krankenkasse, Prämie", "fr": "Assurance-maladie, prime",
                             "it": "Cassa malati, premio"},
    "mahnung": {"de": "Mahnung", "fr": "Sommation", "it": "Richiamo"},
    "unbekannt": {"de": "nicht sicher erkannt", "fr": "pas reconnu avec certitude",
                  "it": "non riconosciuto con certezza"},
}

# Fachbegriffe wie FACHBEGRIFF in nodes/antwort.py
FRIST = {
    "rechtsvorschlag": {"de": "Rechtsvorschlag", "fr": "Opposition", "it": "Opposizione"},
    "zahlung": {"de": "Zahlung", "fr": "Paiement", "it": "Pagamento"},
    "einsprache": {"de": "Einsprache", "fr": "Réclamation", "it": "Reclamo"},
    "kuendigung": {"de": "Kündigung", "fr": "Résiliation", "it": "Disdetta"},
    "franchise_wechsel": {"de": "Wechsel von Franchise oder Modell",
                          "fr": "Changement de franchise ou de modèle",
                          "it": "Cambiamento di franchigia o modello"},
}

BETRAG = {
    "zu_zahlen": {"de": "Betrag", "fr": "Montant", "it": "Importo"},
    "rueckerstattung": {"de": "Rückerstattung", "fr": "Remboursement", "it": "Rimborso"},
    "information": {"de": "Neue Prämie", "fr": "Nouvelle prime", "it": "Nuovo premio"},
}

ZUSTELLUNG_QUELLE = {
    "brief": {"de": "laut Brief", "fr": "selon la lettre", "it": "secondo la lettera"},
    "nutzer": {"de": "Ihre Angabe", "fr": "votre indication", "it": "Sua indicazione"},
    "geschaetzt": {"de": "geschätzt", "fr": "estimée", "it": "stimata"},
}

T = {
    "de": {
        "einleitung": "Die ausführliche Erklärung zu diesem Brief konnte nicht automatisch "
                      "geprüft werden. Deshalb zeigen wir nur die Angaben aus dem Brief und die "
                      "berechneten Fristen.",
        "brief": "Brief", "absender": "Absender", "zustellung": "Zugestellt am",
        "fristen": "Fristen", "keine_fristen": "Keine Frist berechnet.", "bis": "bis",
        "eingang": "muss bis dann beim Empfänger eingetroffen sein",
        "kein_entwurf": "Einen Antwortentwurf können wir für diesen Brief nicht anbieten.",
        "schritte": ["Lesen Sie den Brief selbst und prüfen Sie die Fristen.",
                     "Lassen Sie sich bei Unsicherheit beraten, zum Beispiel beim Absender "
                     "oder bei einer Beratungsstelle."],
    },
    "fr": {
        "einleitung": "L'explication détaillée de cette lettre n'a pas pu être vérifiée "
                      "automatiquement. Nous affichons donc uniquement les informations de la "
                      "lettre et les délais calculés.",
        "brief": "Lettre", "absender": "Expéditeur", "zustellung": "Notifiée le",
        "fristen": "Délais", "keine_fristen": "Aucun délai calculé.", "bis": "jusqu'au",
        "eingang": "doit être arrivé chez le destinataire à cette date",
        "kein_entwurf": "Nous ne pouvons pas proposer de projet de réponse pour cette lettre.",
        "schritte": ["Lisez la lettre vous-même et vérifiez les délais.",
                     "En cas de doute, demandez conseil, par exemple à l'expéditeur ou à un "
                     "service de conseil."],
    },
    "it": {
        "einleitung": "La spiegazione dettagliata di questa lettera non ha potuto essere "
                      "verificata automaticamente. Mostriamo quindi solo i dati della lettera "
                      "e i termini calcolati.",
        "brief": "Lettera", "absender": "Mittente", "zustellung": "Notificata il",
        "fristen": "Termini", "keine_fristen": "Nessun termine calcolato.", "bis": "entro il",
        "eingang": "deve essere arrivato al destinatario entro questa data",
        "kein_entwurf": "Non possiamo proporre una bozza di risposta per questa lettera.",
        "schritte": ["Legga Lei stesso la lettera e verifichi i termini.",
                     "In caso di dubbio si faccia consigliare, ad esempio dal mittente o da un "
                     "servizio di consulenza."],
    },
}


def _datum(d) -> str:
    return d.strftime("%d.%m.%Y")


def _chf(betrag: float) -> str:
    return "CHF " + f"{abs(betrag):,.2f}".replace(",", "'")


def _sprache(state: BriefState) -> str:
    s = state.get("nutzersprache") or state.get("briefsprache") or "de"
    return s if s in T else "de"


def sichere_erklaerung(state: BriefState) -> Erklaerung:
    """Erklärung nur aus geprüften Fakten (Extraktion, Zustelldatum, Fristenrechner)."""
    s = _sprache(state)
    t = T[s]
    ex = state.get("extraktion")
    zeilen = [f"{t['brief']}: {BRIEFTYP.get(state.get('brieftyp'), BRIEFTYP['unbekannt'])[s]}"]
    if ex is not None and ex.absender:
        zeilen.append(f"{t['absender']}: {ex.absender}")
    if ex is not None and ex.hauptbetrag_chf is not None:
        art = BETRAG.get(ex.zahlungsrichtung or "zu_zahlen", BETRAG["zu_zahlen"])[s]
        zeilen.append(f"{art}: {_chf(ex.hauptbetrag_chf)}")
    if state.get("zustelldatum"):
        quelle = ZUSTELLUNG_QUELLE.get(state.get("zustelldatum_quelle"))
        zusatz = f" ({quelle[s]})" if quelle else ""
        zeilen.append(f"{t['zustellung']}: {_datum(state['zustelldatum'])}{zusatz}")

    fristen = state.get("fristen") or []
    if fristen:
        zeilen.append(f"{t['fristen']}:")
        for f in fristen:
            name = FRIST.get(f.art, {}).get(s, f.art)
            zeile = f"- {name}: {t['bis']} {_datum(f.datum)}"
            if "eingang_massgebend" in f.hinweise:
                zeile += f" ({t['eingang']})"
            zeilen.append(zeile)
    else:
        zeilen.append(f"{t['fristen']}: {t['keine_fristen']}")

    text = f"{t['einleitung']}\n\n" + "\n".join(zeilen) + f"\n\n{HINWEIS_PROTOTYP[s]}"
    return Erklaerung(sprache=s, text=text, naechste_schritte=list(t["schritte"]))


def _hinweis_kein_entwurf(erklaerung: Erklaerung, sprache: str) -> Erklaerung:
    """Satz "kein Antwortentwurf" vor dem festen Prototyp-Hinweis einfügen."""
    satz = T[sprache]["kein_entwurf"]
    hinweis = HINWEIS_PROTOTYP[sprache]
    text = erklaerung.text.rstrip()
    if text.endswith(hinweis):
        text = f"{text[:-len(hinweis)].rstrip()}\n\n{satz}\n\n{hinweis}"
    else:
        text = f"{text}\n\n{satz}"
    return erklaerung.model_copy(update={"text": text})


def sichere_ausgabe(state: BriefState) -> dict:
    ergebnis = state.get("guardrail")
    betroffen = {v.betrifft for v in ergebnis.verstoesse} if ergebnis else set()
    update: dict = {"fallback": sorted(betroffen)}

    erklaerung = state.get("erklaerung")
    if "erklaerung" in betroffen or erklaerung is None:
        update["erklaerung_verworfen"] = erklaerung
        erklaerung = sichere_erklaerung(state)
    if "antwortentwurf" in betroffen and state.get("antwortentwurf"):
        update["antwortentwurf_verworfen"] = state["antwortentwurf"]
        update["antwortentwurf"] = None
        erklaerung = _hinweis_kein_entwurf(erklaerung, _sprache(state))
    update["erklaerung"] = erklaerung
    return update
