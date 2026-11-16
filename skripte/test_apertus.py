"""Schneller Verbindungstest fuer die Swiss-AI-API (Apertus).

Liest LLM_BASE_URL, LLM_API_KEY und LLM_MODEL aus der .env,
listet die verfuegbaren Modelle und schickt eine kurze Testfrage.

Aufruf im Projektordner:  python skripte/test_apertus.py
"""
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

base_url = os.environ["LLM_BASE_URL"].rstrip("/")
api_key = os.environ["LLM_API_KEY"]
model = os.environ["LLM_MODEL"]
headers = {"Authorization": f"Bearer {api_key}"}

print(f"Base-URL: {base_url}")
print(f"Modell:   {model}\n")

# 1) Verfuegbare Modelle abfragen
r = requests.get(f"{base_url}/models", headers=headers, timeout=30)
print(f"/models -> HTTP {r.status_code}")
if r.ok:
    ids = [m["id"] for m in r.json().get("data", [])]
    apertus = [i for i in ids if "Apertus" in i]
    print("Apertus-Modelle:")
    for i in apertus:
        print(f"  {i}")
    if model not in ids:
        print(f"\nACHTUNG: '{model}' steht nicht in der Liste. Einen Namen von oben in LLM_MODEL eintragen.")
else:
    print(r.text[:500])
print()

# 2) Kurze Testfrage
r = requests.post(
    f"{base_url}/chat/completions",
    headers=headers,
    json={
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "Erklaere in zwei einfachen Saetzen, was ein Zahlungsbefehl in der Schweiz ist.",
            }
        ],
        "stream": False,
    },
    timeout=120,
)
print(f"/chat/completions -> HTTP {r.status_code}")
if r.ok:
    print(r.json()["choices"][0]["message"]["content"])
else:
    print(r.text[:500])
