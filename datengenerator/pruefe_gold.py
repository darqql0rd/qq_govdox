#!/usr/bin/env python3
"""Prüft alle gold.json: Schema, Summenregel, Datumsformate, keine Privatpersonen in der Extraktion."""
import json, os, re, sys, datetime as dt
from katalog import KATALOG

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "daten", "briefe")
TOP = ["id", "brieftyp", "brieftyp_vermutung", "briefsprache", "injection_verdacht", "extraktion",
       "zustelldatum_annahme", "erwartete_fristen", "testzweck"]
EX = ["absender", "briefdatum", "zustelldatum_im_brief", "referenzen", "periode", "hauptbetrag_chf", "zahlungsrichtung", "posten",
      "frist_im_brief", "glaeubiger", "glaeubiger_vertreter", "forderungsgrund", "zins", "abweichung_von_deklaration",
      "abweichungsgrund", "mahnstufe"]
TYP = {"zahlungsbefehl", "steuerveranlagung", "krankenkasse_praemie", "mahnung", "unbekannt"}
REF = {"betreibung", "steuernummer", "kunde", "police", "debitor", "rechnung", "zahlungsreferenz", "andere"}
FR = {"rechtsvorschlag", "zahlung", "einsprache", "kuendigung", "franchise_wechsel"}
fehler = []


def iso(v, wo):
    if v is not None:
        try: dt.date.fromisoformat(v)
        except Exception: fehler.append(f"{wo}: kein ISO-Datum {v!r}")


for p in KATALOG:
    g = json.load(open(os.path.join(BASE, p["id"], "gold.json"), encoding="utf-8"))
    i = p["id"]; e = g["extraktion"]
    # optional: info_fristen (nur Information, z. B. Fristen ausserhalb des Scopes; wird nicht evaluiert)
    if [k for k in g if k != "info_fristen"] != TOP: fehler.append(f"{i}: Top-Felder {list(g)}")
    for f in g.get("info_fristen", []):
        iso(f["datum"], i)
    if list(e) != EX: fehler.append(f"{i}: Extraktionsfelder")
    if g["brieftyp"] not in TYP: fehler.append(f"{i}: brieftyp")
    if (g["brieftyp"] == "unbekannt") != bool(g["brieftyp_vermutung"]):
        fehler.append(f"{i}: brieftyp_vermutung nur (und immer) bei Typ unbekannt")
    if g["injection_verdacht"] != bool(p.get("injection")): fehler.append(f"{i}: injection_verdacht")
    for r in e["referenzen"]:
        if r["art"] not in REF: fehler.append(f"{i}: ref art {r['art']}")
    for f in g["erwartete_fristen"]:
        if f["art"] not in FR: fehler.append(f"{i}: frist art {f['art']}")
        iso(f["datum"], i)
    for k in ["briefdatum", "zustelldatum_im_brief", "frist_im_brief"]: iso(e[k], f"{i}.{k}")
    iso(g["zustelldatum_annahme"], i)
    if e["posten"] and e["hauptbetrag_chf"] is not None and g["brieftyp"] != "krankenkasse_praemie":
        s = round(sum(x["betrag_chf"] for x in e["posten"]), 2)
        if abs(s - e["hauptbetrag_chf"]) > 0.005: fehler.append(f"{i}: Summe {s} != {e['hauptbetrag_chf']}")
    # Privatpersonen: Nachnamen aus Empfängerzeile dürfen nicht in der Extraktion stehen
    blob = json.dumps(e, ensure_ascii=False)
    empf = p.get("empf") or p["schuldner"]["empf"]
    privat = empf[0] in {"Herr", "Frau", "Herr und Frau", "Madame", "Monsieur", "Monsieur et Madame", "Famille",
                         "Signor", "Signora", "Signori"}
    namen = re.findall(r"[A-ZÄÖÜ][a-zäöüéèàì]+", empf[1]) + re.findall(r"[A-ZÄÖÜ][a-zäöüéèàì]+", empf[2]) if privat else []
    for n in namen:
        if len(n) > 3 and re.search(r"\b" + n + r"\b", blob) and n not in {"Strada", "Chemin", "Route", "Via"}:
            fehler.append(f"{i}: Privatname '{n}' in Extraktion")
    if p["typ"] != "neg":
        txt = open(os.path.join(BASE, i, "text.txt"), encoding="utf-8").read()
        if "Synthet" not in txt and "synthét" not in txt and "sintetic" not in txt:
            fehler.append(f"{i}: Fusszeile fehlt im Text")

print("\n".join(fehler) if fehler else f"OK: {len(KATALOG)} gold.json geprüft")
sys.exit(1 if fehler else 0)
