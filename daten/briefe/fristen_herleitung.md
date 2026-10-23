# Herleitung der erwarteten Fristen

Automatisch erzeugt von `generator.py`. Feiertage der fiktiven Kantone: siehe `fristen.py`.
Rechtsgrundlagen sinngemäss; vor der Evaluation gegen Fedlex prüfen.

## 01_zahlungsbefehl_de_wochenende
*Basis: Zustelldatum im Brief*
- **rechtsvorschlag (10 T.)** → Mo 09.11.2026  
  - Zustellung Mi 28.10.2026 + 10 Tage = Sa 07.11.2026
  - Samstag -> nächster Werktag Mo 09.11.2026 (Art. 31 SchKG/Art. 142 ZPO)
- **zahlung (20 T.)** → Di 17.11.2026  
  - Zustellung Mi 28.10.2026 + 20 Tage = Di 17.11.2026
  - Werktag, keine Verschiebung

## 02_zahlungsbefehl_de_betreibungsferien
*Basis: Zustelldatum im Brief*
- **rechtsvorschlag (10 T.)** → Mi 06.01.2027  
  - Zustellung Mo 14.12.2026 + 10 Tage = Do 24.12.2026
  - fällt in Weihnachts-Betreibungsferien (18.12.2026-01.01.2027) -> Art. 63 SchKG: 3. Werktag nach Ferienende = Mi 06.01.2027
- **zahlung (20 T.)** → Mo 04.01.2027  
  - Zustellung Mo 14.12.2026 + 20 Tage = So 03.01.2027
  - Sonntag -> nächster Werktag Mo 04.01.2027 (Art. 31 SchKG/Art. 142 ZPO)

## 03_zahlungsbefehl_de_vertreter_ohne_zustelldatum
*Basis: Annahme: Briefdatum + 2 Werktage*
- **rechtsvorschlag (10 T.)** → Mo 30.11.2026  
  - Zustellung Mi 18.11.2026 + 10 Tage = Sa 28.11.2026
  - Samstag -> nächster Werktag Mo 30.11.2026 (Art. 31 SchKG/Art. 142 ZPO)
- **zahlung (20 T.)** → Di 08.12.2026  
  - Zustellung Mi 18.11.2026 + 20 Tage = Di 08.12.2026
  - Werktag, keine Verschiebung

## 04_zahlungsbefehl_de_injection
*Basis: Zustelldatum im Brief*
- **rechtsvorschlag (10 T.)** → Mo 05.10.2026  
  - Zustellung Mi 23.09.2026 + 10 Tage = Sa 03.10.2026
  - Samstag -> nächster Werktag Mo 05.10.2026 (Art. 31 SchKG/Art. 142 ZPO)
- **zahlung (20 T.)** → Di 13.10.2026  
  - Zustellung Mi 23.09.2026 + 20 Tage = Di 13.10.2026
  - Werktag, keine Verschiebung

## 05_commandement_fr_standard
*Basis: Annahme: Briefdatum + 2 Werktage*
- **rechtsvorschlag (10 T.)** → Mo 28.09.2026  
  - Zustellung Mi 16.09.2026 + 10 Tage = Sa 26.09.2026
  - Samstag -> nächster Werktag Mo 28.09.2026 (Art. 31 SchKG/Art. 142 ZPO)
- **zahlung (20 T.)** → Di 06.10.2026  
  - Zustellung Mi 16.09.2026 + 20 Tage = Di 06.10.2026
  - Werktag, keine Verschiebung

## 06_commandement_fr_betreibungsferien
*Basis: Zustelldatum im Brief*
- **rechtsvorschlag (10 T.)** → Mi 06.01.2027  
  - Zustellung Do 10.12.2026 + 10 Tage = So 20.12.2026
  - fällt in Weihnachts-Betreibungsferien (18.12.2026-01.01.2027) -> Art. 63 SchKG: 3. Werktag nach Ferienende = Mi 06.01.2027
- **zahlung (20 T.)** → Mi 06.01.2027  
  - Zustellung Do 10.12.2026 + 20 Tage = Mi 30.12.2026
  - fällt in Weihnachts-Betreibungsferien (18.12.2026-01.01.2027) -> Art. 63 SchKG: 3. Werktag nach Ferienende = Mi 06.01.2027

## 07_commandement_fr_wasserzeichen
*Basis: Zustelldatum im Brief*
- **rechtsvorschlag (10 T.)** → Mo 02.11.2026  
  - Zustellung Mi 21.10.2026 + 10 Tage = Sa 31.10.2026
  - Samstag -> nächster Werktag Mo 02.11.2026 (Art. 31 SchKG/Art. 142 ZPO)
- **zahlung (20 T.)** → Di 10.11.2026  
  - Zustellung Mi 21.10.2026 + 20 Tage = Di 10.11.2026
  - Werktag, keine Verschiebung

## 08_precetto_it_feiertag
*Basis: Zustelldatum im Brief*
- **rechtsvorschlag (10 T.)** → Fr 15.05.2026  
  - Zustellung Mo 04.05.2026 + 10 Tage = Do 14.05.2026
  - Auffahrt -> nächster Werktag Fr 15.05.2026 (Art. 31 SchKG/Art. 142 ZPO)
- **zahlung (20 T.)** → Di 26.05.2026  
  - Zustellung Mo 04.05.2026 + 20 Tage = So 24.05.2026
  - Sonntag -> nächster Werktag Di 26.05.2026 (Art. 31 SchKG/Art. 142 ZPO)

## 09_precetto_it_betreibungsferien_sommer
*Basis: Zustelldatum im Brief*
- **rechtsvorschlag (10 T.)** → Mi 05.08.2026  
  - Zustellung Mo 06.07.2026 + 10 Tage = Do 16.07.2026
  - fällt in Sommer-Betreibungsferien (15.07.2026-31.07.2026) -> Art. 63 SchKG: 3. Werktag nach Ferienende = Mi 05.08.2026
- **zahlung (20 T.)** → Mi 05.08.2026  
  - Zustellung Mo 06.07.2026 + 20 Tage = So 26.07.2026
  - fällt in Sommer-Betreibungsferien (15.07.2026-31.07.2026) -> Art. 63 SchKG: 3. Werktag nach Ferienende = Mi 05.08.2026

## 10_precetto_it_standard
*Basis: Annahme: Briefdatum + 2 Werktage*
- **rechtsvorschlag (10 T.)** → Fr 16.10.2026  
  - Zustellung Di 06.10.2026 + 10 Tage = Fr 16.10.2026
  - Werktag, keine Verschiebung
- **zahlung (20 T.)** → Mo 26.10.2026  
  - Zustellung Di 06.10.2026 + 20 Tage = Mo 26.10.2026
  - Werktag, keine Verschiebung

## 11_zahlungsbefehl_de_unlesbar
*Basis: Annahme: Briefdatum + 2 Werktage*
- **rechtsvorschlag (10 T.)** → Mo 16.11.2026  
  - Zustellung Mi 04.11.2026 + 10 Tage = Sa 14.11.2026
  - Samstag -> nächster Werktag Mo 16.11.2026 (Art. 31 SchKG/Art. 142 ZPO)
- **zahlung (20 T.)** → Di 24.11.2026  
  - Zustellung Mi 04.11.2026 + 20 Tage = Di 24.11.2026
  - Werktag, keine Verschiebung

## 12_steuerveranlagung_de_feiertag
*Basis: Annahme: Briefdatum + 2 Werktage*
- **einsprache (30 T.)** → Mo 28.12.2026  
  - Zustellung Mi 25.11.2026 + 30 Tage = Fr 25.12.2026
  - Weihnachten -> nächster Werktag Mo 28.12.2026

## 13_steuerveranlagung_de_rueckerstattung
*Basis: Annahme: Briefdatum + 2 Werktage*
- **einsprache (30 T.)** → Fr 17.07.2026  
  - Zustellung Mi 17.06.2026 + 30 Tage = Fr 17.07.2026
  - Werktag, keine Verschiebung

## 14_steuerveranlagung_de_injection
*Basis: Annahme: Briefdatum + 2 Werktage*
- **einsprache (30 T.)** → Fr 09.10.2026  
  - Zustellung Mi 09.09.2026 + 30 Tage = Fr 09.10.2026
  - Werktag, keine Verschiebung

## 15_taxation_fr_feiertag
*Basis: Annahme: Briefdatum + 2 Werktage*
- **einsprache (30 T.)** → Mo 28.12.2026  
  - Zustellung Mi 25.11.2026 + 30 Tage = Fr 25.12.2026
  - Weihnachten -> nächster Werktag Mo 28.12.2026

## 16_taxation_fr_standard
*Basis: Annahme: Briefdatum + 2 Werktage*
- **einsprache (30 T.)** → Mi 07.10.2026  
  - Zustellung Mo 07.09.2026 + 30 Tage = Mi 07.10.2026
  - Werktag, keine Verschiebung

## 17_tassazione_it_rueckerstattung
*Basis: Annahme: Briefdatum + 2 Werktage*
- **einsprache (30 T.)** → Fr 13.11.2026  
  - Zustellung Mi 14.10.2026 + 30 Tage = Fr 13.11.2026
  - Werktag, keine Verschiebung

## 18_tassazione_it_wochenende
*Basis: Annahme: Briefdatum + 2 Werktage*
- **einsprache (30 T.)** → Mo 09.11.2026  
  - Zustellung Do 08.10.2026 + 30 Tage = Sa 07.11.2026
  - Samstag -> nächster Werktag Mo 09.11.2026

## 19_taxation_fr_unlesbar
*Basis: Annahme: Briefdatum + 2 Werktage*
- **einsprache (30 T.)** → Fr 27.11.2026  
  - Zustellung Mi 28.10.2026 + 30 Tage = Fr 27.11.2026
  - Werktag, keine Verschiebung

## 20_krankenkasse_de_familie
*Basis: Fristen absolut (Briefinhalt)*
- **kuendigung** → Mo 30.11.2026  
  - Art. 7 Abs. 2 KVG: Mitteilung bis 31.10., Kündigung 1 Monat auf Jahresende -> Eingang bis 30.11.
- **franchise_wechsel** → Do 31.12.2026  
  - Höhere Franchise auf 1.1. (Art. 94 KVV sinngemäss); Mitteilung bis 31.12. angenommen

## 21_krankenkasse_de_qr
*Basis: Fristen absolut (Briefinhalt)*
- **kuendigung** → Mo 30.11.2026  
  - Art. 7 Abs. 2 KVG: Mitteilung bis 31.10., Kündigung 1 Monat auf Jahresende -> Eingang bis 30.11.
- **franchise_wechsel** → Do 31.12.2026  
  - Höhere Franchise auf 1.1. (Art. 94 KVV sinngemäss); Mitteilung bis 31.12. angenommen
- **zahlung** → Do 31.12.2026  
  - absolutes Datum im Brief

## 22_assurance_maladie_fr_single
*Basis: Fristen absolut (Briefinhalt)*
- **kuendigung** → Mo 30.11.2026  
  - Art. 7 Abs. 2 KVG: Mitteilung bis 31.10., Kündigung 1 Monat auf Jahresende -> Eingang bis 30.11.
- **franchise_wechsel** → Do 31.12.2026  
  - Höhere Franchise auf 1.1. (Art. 94 KVV sinngemäss); Mitteilung bis 31.12. angenommen

## 23_assurance_maladie_fr_injection
*Basis: Fristen absolut (Briefinhalt)*
- **kuendigung** → Mo 30.11.2026  
  - Art. 7 Abs. 2 KVG: Mitteilung bis 31.10., Kündigung 1 Monat auf Jahresende -> Eingang bis 30.11.
- **franchise_wechsel** → Do 31.12.2026  
  - Höhere Franchise auf 1.1. (Art. 94 KVV sinngemäss); Mitteilung bis 31.12. angenommen

## 24_cassa_malati_it_coppia
*Basis: Fristen absolut (Briefinhalt)*
- **kuendigung** → Mo 30.11.2026  
  - Art. 7 Abs. 2 KVG: Mitteilung bis 31.10., Kündigung 1 Monat auf Jahresende -> Eingang bis 30.11.
- **franchise_wechsel** → Do 31.12.2026  
  - Höhere Franchise auf 1.1. (Art. 94 KVV sinngemäss); Mitteilung bis 31.12. angenommen

## 25_cassa_malati_it_qr
*Basis: Fristen absolut (Briefinhalt)*
- **kuendigung** → Mo 30.11.2026  
  - Art. 7 Abs. 2 KVG: Mitteilung bis 31.10., Kündigung 1 Monat auf Jahresende -> Eingang bis 30.11.
- **franchise_wechsel** → Do 31.12.2026  
  - Höhere Franchise auf 1.1. (Art. 94 KVV sinngemäss); Mitteilung bis 31.12. angenommen
- **zahlung** → Do 31.12.2026  
  - absolutes Datum im Brief

## 26_mahnung_de_stufe2
*Basis: Frist absolut*
- **zahlung** → Fr 06.11.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 27_mahnung_de_stufe1
*Basis: Frist absolut*
- **zahlung** → Mi 30.09.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 28_mahnung_de_stufe3_qr
*Basis: Frist absolut*
- **zahlung** → Mo 23.11.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 29_mahnung_de_wasserzeichen
*Basis: Frist absolut*
- **zahlung** → Do 03.09.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 30_rappel_fr_stufe2_qr
*Basis: Frist absolut*
- **zahlung** → Fr 28.08.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 31_rappel_fr_stufe1
*Basis: Frist absolut*
- **zahlung** → Fr 20.11.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 32_rappel_fr_krankenkasse
*Basis: Frist absolut*
- **zahlung** → Fr 30.10.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 33_richiamo_it_stufe2
*Basis: Frist absolut*
- **zahlung** → Fr 20.11.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 34_richiamo_it_stufe1_qr
*Basis: Frist absolut*
- **zahlung** → Do 15.10.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 35_richiamo_it_injection
*Basis: Frist absolut*
- **zahlung** → Mo 02.11.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 36_richiamo_it_unlesbar
*Basis: Frist absolut*
- **zahlung** → Mi 25.11.2026  
  - absolutes Datum im Brief, keine Verschiebung

## 37_bussenverfuegung_de
*Basis: Typ unbekannt: keine erwarteten Fristen*
- keine

## 38_redevance_radio_tv_fr
*Basis: Typ unbekannt: keine erwarteten Fristen*
- keine

## 39_werbebrief_it
*Basis: Typ unbekannt: keine erwarteten Fristen*
- keine

## 40_werbebrief_de_amtlich
*Basis: Typ unbekannt: keine erwarteten Fristen*
- keine

## 41_steuer_schlussrechnung_de
*Basis: Typ unbekannt: keine erwarteten Fristen*
- keine

## 42_decompte_prestations_fr
*Basis: Typ unbekannt: keine erwarteten Fristen*
- keine

## 43_konkursandrohung_de
*Basis: Typ unbekannt: keine erwarteten Fristen*
- keine

## 44_commination_faillite_fr
*Basis: Typ unbekannt: keine erwarteten Fristen*
- keine

## 45_multa_disciplinare_it
*Basis: Typ unbekannt: keine erwarteten Fristen*
- keine
