"""Einfache Web-Oberfläche für den Behördenbrief-Erklärer (Owner: Florian).

    pip install streamlit
    streamlit run app.py

Die UI ruft nur den Graphen auf (wie main.py) und zeigt seine Fragen als Eingabefelder:
Der Graph hält bei interrupt() an (Zustelldatum, Bestätigung), die UI zeigt die Frage,
ein Klick setzt ihn mit Command(resume=...) fort. Ein Thread pro Brief (thread_id).

Fristen stehen oben in einem eigenen Kasten: Sie kommen aus dem Fristenrechner, nicht vom LLM.
"""

import tempfile
from datetime import date
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

load_dotenv()  # vor den LangChain-Imports, damit LangSmith-Tracing aktiv ist

import streamlit as st                      # noqa: E402
from langgraph.types import Command         # noqa: E402

from graph import baue_graph                # noqa: E402
from mocks import DATEN, fall_ids           # noqa: E402
from nodes.sichere_ausgabe import BETRAG, BRIEFTYP, FRIST, ZUSTELLUNG_QUELLE, _chf  # noqa: E402
from prompts import HINWEIS_PROTOTYP          # noqa: E402

SPRACHEN = {"de": "Deutsch", "fr": "Français", "it": "Italiano"}
SCHRITTE = {  # Fortschrittsanzeige pro Node
    "ocr": "Brief lesen", "analyse": "Brief verstehen", "fristen": "Fristen berechnen",
    "erklaerung": "Erklärung schreiben", "antwort": "Antwortentwurf schreiben",
    "guardrail": "Texte prüfen", "sichere_ausgabe": "Sichere Ausgabe", "kalender": "Kalender",
}

st.set_page_config(page_title="Behördenbrief verstehen", page_icon="✉️", layout="centered")


@st.cache_resource
def graph():
    return baue_graph()


def neu():
    for k in ("thread", "pfade", "frage", "werte", "fertig"):
        st.session_state.pop(k, None)


def config() -> dict:
    return {"configurable": {"thread_id": st.session_state.thread},
            "run_name": "ui", "tags": ["ui"]}


def ausfuehren(eingabe):
    """Graph laufen lassen, bis er fertig ist oder eine Frage stellt."""
    with st.status("Brief wird verarbeitet …", expanded=True) as status:
        try:
            for teil in graph().stream(eingabe, config(), stream_mode="updates"):
                for node in teil:
                    if node in SCHRITTE:
                        st.write(f"✓ {SCHRITTE[node]}")
        except Exception as fehler:  # z. B. LLM-Proxy nicht erreichbar
            status.update(label="Fehler", state="error")
            st.error(f"{type(fehler).__name__}: {str(fehler)[:300]}")
            return
        status.update(label="Fertig", state="complete", expanded=False)
    snap = graph().get_state(config())
    fragen = [i for t in snap.tasks for i in t.interrupts]
    st.session_state.werte = snap.values
    st.session_state.frage = fragen[0].value if fragen else None
    st.session_state.fertig = not snap.next


def datum(d) -> str:
    return d.strftime("%d.%m.%Y")


# ---------------------------------------------------------------------------
# Anzeige des Ergebnisses
# ---------------------------------------------------------------------------

def zeige_ergebnis(w: dict):
    sprache = "de"  # Oberfläche Deutsch; nur die Erklärung kommt in der gewählten Sprache
    if not w.get("text_lesbar", True):
        st.error("Der Brief ist nicht lesbar. Bitte laden Sie ein schärferes Foto hoch "
                 "(gerade, gut beleuchtet, ganze Seite).")
        return
    if w.get("injection_verdacht"):
        st.warning("Der Brief enthält Text, der wie eine Anweisung an ein Computerprogramm "
                   "aussieht. Wir haben ihn ignoriert. Prüfen Sie den Brief bitte besonders genau.")
    if w.get("fallback"):
        st.info("Die ausführliche Erklärung konnte nicht automatisch geprüft werden. "
                "Wir zeigen deshalb nur die Angaben aus dem Brief und die berechneten Fristen.")

    typ = w.get("brieftyp")
    ex = w.get("extraktion")
    kopf = BRIEFTYP.get(typ, BRIEFTYP["unbekannt"])[sprache]
    if typ == "unbekannt" and w.get("brieftyp_vermutung"):
        kopf = w["brieftyp_vermutung"]
    st.subheader(kopf)
    unterzeile = [ex.absender] if ex is not None and ex.absender else []
    if ex is not None and ex.hauptbetrag_chf is not None:
        art = BETRAG.get(ex.zahlungsrichtung or "zu_zahlen", BETRAG["zu_zahlen"])[sprache]
        unterzeile.append(f"{art}: {_chf(ex.hauptbetrag_chf)}")
    if unterzeile:
        st.caption(" · ".join(unterzeile))

    fristen = w.get("fristen") or []
    if fristen:
        with st.container(border=True):
            st.markdown("**Fristen**")
            for f in fristen:
                name = FRIST.get(f.art, {}).get(sprache, f.art)
                links, rechts = st.columns([3, 2])
                links.write(name)
                rechts.markdown(f"**bis {datum(f.datum)}**")
                if "eingang_massgebend" in f.hinweise:
                    st.caption("Muss bis zu diesem Tag beim Empfänger eingetroffen sein.")
            if w.get("zustelldatum"):
                quelle = ZUSTELLUNG_QUELLE.get(w.get("zustelldatum_quelle"), {}).get(sprache, "")
                st.caption(f"Zugestellt am {datum(w['zustelldatum'])}"
                           + (f" ({quelle})" if quelle else ""))

    e = w.get("erklaerung")
    hinweis = None
    if e:
        text = e.text
        for h in HINWEIS_PROTOTYP.values():  # Prototyp-Hinweis als Fussnote statt im Text
            if h in text:
                text, hinweis = text.replace(h, "").strip(), h
        # Beim Fallback steht alles Wichtige schon im Kasten oben
        if "erklaerung" not in (w.get("fallback") or []):
            st.markdown("**Erklärung**")
            # $ würde Streamlit als Formel lesen
            st.markdown(text.replace("$", r"\$").replace("\n", "  \n"))
        if e.naechste_schritte:
            st.markdown("**Nächste Schritte**")
            st.markdown("\n".join(f"- {s}" for s in e.naechste_schritte))

    entwurf = w.get("antwortentwurf")
    if entwurf:
        with st.expander(f"Antwortentwurf: {entwurf.betreff}"):
            st.caption("Ergänzen Sie die Angaben in [eckigen Klammern], prüfen Sie den Text "
                       "und unterschreiben Sie ihn selbst.")
            st.code(entwurf.text, language=None, wrap_lines=True)
            st.download_button("Als Textdatei herunterladen", entwurf.text,
                               file_name="antwortentwurf.txt", mime="text/plain")
    if hinweis:
        st.caption(hinweis)


# ---------------------------------------------------------------------------
# Seite
# ---------------------------------------------------------------------------

st.title("✉️ Behördenbrief verstehen")
sprache = st.selectbox("Sprache der Erklärung", list(SPRACHEN), format_func=SPRACHEN.get,
                       disabled="thread" in st.session_state)

# 1. Brief wählen
if "thread" not in st.session_state:
    eigener, beispiel = st.tabs(["Eigener Brief", "Beispielbrief"])
    with eigener:
        dateien = st.file_uploader("PDF oder Fotos (eine Datei pro Seite)",
                                   type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)
        if st.button("Brief erklären", type="primary", disabled=not dateien, key="los_eigen"):
            ordner = Path(tempfile.mkdtemp(prefix="govdox_"))
            pfade = []
            for d in sorted(dateien, key=lambda d: d.name):
                pfad = ordner / Path(d.name).name
                pfad.write_bytes(d.getvalue())
                pfade.append(str(pfad))
            st.session_state.pfade = pfade
    with beispiel:
        fall = st.selectbox("Testbrief", fall_ids())
        variante = st.radio("Vorlage", ["PDF", "Foto"], horizontal=True,
                            help="Foto: mit Texterkennung (docTR), dauert beim ersten Mal länger")
        if st.button("Brief erklären", type="primary", key="los_beispiel"):
            ordner = DATEN / fall
            if variante == "PDF":
                pfade = [ordner / "brief.pdf"]
            else:
                pfade = sorted(ordner.glob("foto*.jpg"), key=lambda p: (len(p.name), p.name))
            st.session_state.pfade = [str(p) for p in pfade]
    if "pfade" in st.session_state:
        st.session_state.thread = uuid4().hex
        ausfuehren({"dokument_pfade": st.session_state.pfade, "nutzersprache": sprache})
        st.rerun()
    st.stop()

w = st.session_state.get("werte", {})
frage = st.session_state.get("frage")

# 2. Zustelldatum erfragen
if frage and frage["typ"] == "zustelldatum":
    with st.container(border=True):
        st.markdown(f"**{frage['frage'].split('(')[0].strip()}**")
        st.caption("Die Frist läuft ab dem Tag, an dem Sie den Brief erhalten haben.")
        weiss_nicht = st.checkbox("Weiss ich nicht")
        tag = st.date_input("Erhalten am", value=date.today(), format="DD.MM.YYYY",
                            disabled=weiss_nicht)
        if st.button("Weiter", type="primary"):
            ausfuehren(Command(resume="weiss nicht" if weiss_nicht else datum(tag)))
            st.rerun()
    st.stop()

# 3. Ergebnis
zeige_ergebnis(w)

# 4. Bestätigung und Kalender
if frage and frage["typ"] == "bestaetigung":
    st.divider()
    st.markdown("**Stimmen diese Fristen? Sollen sie in Ihren Kalender eingetragen werden?**")
    ja, nein = st.columns(2)
    if ja.button("Ja, in den Kalender", type="primary", use_container_width=True):
        ausfuehren(Command(resume="ja"))
        st.rerun()
    if nein.button("Nein", use_container_width=True):
        ausfuehren(Command(resume="nein"))
        st.rerun()

k = w.get("kalender")
if k and k.ics_pfad and Path(k.ics_pfad).exists():
    st.success("Die Fristen sind bereit für Ihren Kalender.")
    st.download_button("📅 Kalenderdatei (.ics) herunterladen", Path(k.ics_pfad).read_bytes(),
                       file_name=Path(k.ics_pfad).name, mime="text/calendar")
elif k and k.event_ids:
    st.success(f"{len(k.event_ids)} Termin(e) im Google Kalender eingetragen.")
elif w.get("abbruch_grund") == "nicht_bestaetigt":
    st.info("Es wurde nichts in den Kalender eingetragen.")

if st.session_state.get("fertig") or not frage:
    st.divider()
    st.button("Neuen Brief erklären", on_click=neu)
