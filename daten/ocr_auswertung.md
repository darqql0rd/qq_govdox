# OCR-Auswertung

docTR (fast_base + PARSeq multilingual), Lesbarkeit: Konfidenz ≥ 0.75 (mittlere Wortkonfidenz × min(1, Wörter / (80 × Seiten))). Ähnlichkeit = difflib.SequenceMatcher zu text.txt, Leerraum normalisiert.

## Zusammenfassung

| Variante | Briefe | Ø Ähnlichkeit | Median | Minimum | Lesbarkeit korrekt | Ø Sekunden |
|---|---|---|---|---|---|---|
| pdf | 45 | 0.884 | 0.904 | 0.745 | 45/45 | 0.1 |
| scan | 45 | 0.982 | 0.986 | 0.925 | 45/45 | 6.9 |
| foto | 45 | 0.918 | 0.913 | 0.839 | 45/45 | 6.5 |

Ø, Median und Minimum ohne die absichtlich unlesbaren Fotos (11, 19, 36).

## Pro Brief

| Brief | pdf Ähnl. | pdf Konf. | pdf lesbar | scan Ähnl. | scan Konf. | scan lesbar | foto Ähnl. | foto Konf. | foto lesbar |
|---|---|---|---|---|---|---|---|---|---|
| 01_zahlungsbefehl_de_wochenende | 0.954 | – | ja | 0.985 | 0.99 | ja | 0.948 | 0.98 | ja |
| 02_zahlungsbefehl_de_betreibungsferien | 0.905 | – | ja | 0.982 | 0.99 | ja | 0.922 | 0.97 | ja |
| 03_zahlungsbefehl_de_vertreter_ohne_zustelldatum | 0.941 | – | ja | 0.972 | 1.00 | ja | 0.922 | 0.99 | ja |
| 04_zahlungsbefehl_de_injection | 0.957 | – | ja | 0.979 | 0.99 | ja | 0.886 | 0.98 | ja |
| 05_commandement_fr_standard | 0.956 | – | ja | 0.970 | 0.99 | ja | 0.888 | 0.97 | ja |
| 06_commandement_fr_betreibungsferien | 0.936 | – | ja | 0.973 | 0.99 | ja | 0.894 | 0.98 | ja |
| 07_commandement_fr_wasserzeichen | 0.887 | – | ja | 0.938 | 0.98 | ja | 0.882 | 0.98 | ja |
| 08_precetto_it_feiertag | 0.954 | – | ja | 0.979 | 0.99 | ja | 0.913 | 0.98 | ja |
| 09_precetto_it_betreibungsferien_sommer | 0.953 | – | ja | 0.979 | 0.99 | ja | 0.910 | 0.97 | ja |
| 10_precetto_it_standard | 0.937 | – | ja | 0.962 | 0.99 | ja | 0.918 | 0.98 | ja |
| 11_zahlungsbefehl_de_unlesbar | 0.953 | – | ja | 0.978 | 0.99 | ja | 0.194 | 0.18 | nein |
| 12_steuerveranlagung_de_feiertag | 0.949 | – | ja | 0.998 | 1.00 | ja | 0.978 | 0.99 | ja |
| 13_steuerveranlagung_de_rueckerstattung | 0.841 | – | ja | 0.995 | 0.99 | ja | 0.961 | 0.99 | ja |
| 14_steuerveranlagung_de_injection | 0.953 | – | ja | 0.954 | 1.00 | ja | 0.852 | 0.98 | ja |
| 15_taxation_fr_feiertag | 0.930 | – | ja | 0.991 | 0.99 | ja | 0.866 | 0.98 | ja |
| 16_taxation_fr_standard | 0.945 | – | ja | 0.993 | 0.99 | ja | 0.897 | 0.98 | ja |
| 17_tassazione_it_rueckerstattung | 0.834 | – | ja | 0.996 | 1.00 | ja | 0.906 | 0.98 | ja |
| 18_tassazione_it_wochenende | 0.949 | – | ja | 0.995 | 1.00 | ja | 0.914 | 0.98 | ja |
| 19_taxation_fr_unlesbar | 0.939 | – | ja | 0.994 | 0.99 | ja | 0.479 | 0.65 | nein |
| 20_krankenkasse_de_familie | 0.934 | – | ja | 0.995 | 0.99 | ja | 0.968 | 0.98 | ja |
| 21_krankenkasse_de_qr | 0.853 | – | ja | 0.980 | 0.99 | ja | 0.960 | 0.98 | ja |
| 22_assurance_maladie_fr_single | 0.846 | – | ja | 0.993 | 0.99 | ja | 0.980 | 0.99 | ja |
| 23_assurance_maladie_fr_injection | 0.939 | – | ja | 0.990 | 0.99 | ja | 0.940 | 0.98 | ja |
| 24_cassa_malati_it_coppia | 0.904 | – | ja | 0.985 | 0.99 | ja | 0.978 | 0.99 | ja |
| 25_cassa_malati_it_qr | 0.857 | – | ja | 0.986 | 0.99 | ja | 0.844 | 0.97 | ja |
| 26_mahnung_de_stufe2 | 0.916 | – | ja | 0.998 | 1.00 | ja | 0.986 | 0.99 | ja |
| 27_mahnung_de_stufe1 | 0.802 | – | ja | 0.993 | 0.99 | ja | 0.908 | 0.98 | ja |
| 28_mahnung_de_stufe3_qr | 0.826 | – | ja | 0.980 | 0.99 | ja | 0.970 | 0.99 | ja |
| 29_mahnung_de_wasserzeichen | 0.845 | – | ja | 0.948 | 1.00 | ja | 0.852 | 0.98 | ja |
| 30_rappel_fr_stufe2_qr | 0.831 | – | ja | 0.980 | 0.99 | ja | 0.902 | 0.98 | ja |
| 31_rappel_fr_stufe1 | 0.752 | – | ja | 0.995 | 0.99 | ja | 0.951 | 0.98 | ja |
| 32_rappel_fr_krankenkasse | 0.896 | – | ja | 0.981 | 0.99 | ja | 0.897 | 0.97 | ja |
| 33_richiamo_it_stufe2 | 0.917 | – | ja | 0.994 | 1.00 | ja | 0.966 | 0.99 | ja |
| 34_richiamo_it_stufe1_qr | 0.745 | – | ja | 0.962 | 0.99 | ja | 0.877 | 0.97 | ja |
| 35_richiamo_it_injection | 0.926 | – | ja | 0.925 | 0.99 | ja | 0.876 | 0.97 | ja |
| 36_richiamo_it_unlesbar | 0.820 | – | ja | 0.997 | 0.99 | ja | 0.000 | 0.00 | nein |
| 37_bussenverfuegung_de | 0.852 | – | ja | 0.996 | 0.99 | ja | 0.977 | 0.99 | ja |
| 38_redevance_radio_tv_fr | 0.862 | – | ja | 0.992 | 0.99 | ja | 0.955 | 0.98 | ja |
| 39_werbebrief_it | 0.870 | – | ja | 0.967 | 0.99 | ja | 0.884 | 0.98 | ja |
| 40_werbebrief_de_amtlich | 0.793 | – | ja | 0.966 | 0.99 | ja | 0.859 | 0.98 | ja |
| 41_steuer_schlussrechnung_de | 0.802 | – | ja | 0.989 | 0.99 | ja | 0.879 | 0.99 | ja |
| 42_decompte_prestations_fr | 0.809 | – | ja | 0.997 | 0.99 | ja | 0.908 | 0.98 | ja |
| 43_konkursandrohung_de | 0.906 | – | ja | 0.998 | 1.00 | ja | 0.980 | 0.99 | ja |
| 44_commination_faillite_fr | 0.770 | – | ja | 0.993 | 1.00 | ja | 0.839 | 0.98 | ja |
| 45_multa_disciplinare_it | 0.842 | – | ja | 0.993 | 1.00 | ja | 0.955 | 0.98 | ja |
