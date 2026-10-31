"""Misst, wie gut Kundennotizen in Positionen übersetzt werden.

    python evaluieren.py                 # Regelbasiert, Dev- und Holdout-Set
    python evaluieren.py --modus llm     # mit Sprachmodell (OPENAI_API_KEY nötig)

Eine Position zählt als richtig, wenn Raum, Komponente und Anzahl stimmen.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from wp import aenderung, llm, regeln
from wp.schema import Position

DATEN = Path(__file__).parent / "data" / "eval"


def laden(name: str) -> list[dict]:
    return [json.loads(z) for z in (DATEN / name).read_text(encoding="utf-8").splitlines() if z.strip()]


def als_menge(positionen) -> Counter:
    return Counter((p["raum"], p["komponente"], p["anzahl"]) if isinstance(p, dict) else (p.raum, p.komponente, p.anzahl)
                   for p in positionen)


def bewerten(paare: list[tuple[Counter, Counter]]) -> dict:
    tp = sum(sum((soll & ist).values()) for soll, ist in paare)
    n_soll = sum(sum(soll.values()) for soll, _ in paare)
    n_ist = sum(sum(ist.values()) for _, ist in paare)
    p, r = tp / n_ist if n_ist else 0.0, tp / n_soll if n_soll else 0.0
    exakt = sum(soll == ist for soll, ist in paare)
    return {"precision": p, "recall": r, "f1": 2 * p * r / (p + r) if p + r else 0.0, "exakt": f"{exakt}/{len(paare)}"}


def extraktion(name: str, modus: str, zeigen: bool) -> dict:
    paare = []
    for fall in laden(name):
        plan = llm.extrahieren(fall["text"]) if modus == "llm" else regeln.extrahieren(fall["text"])
        soll, ist = als_menge(fall["positionen"]), als_menge(plan.positionen)
        if zeigen and soll != ist:
            print(f"  {fall['id']}: fehlt {dict(soll - ist)} | zu viel {dict(ist - soll)}")
        paare.append((soll, ist))
    return bewerten(paare)


def aenderungen(name: str, modus: str, zeigen: bool) -> dict:
    paare = []
    for fall in laden(name):
        vorher = [Position(**p) for p in fall["vorher"]]
        nachher = (llm.aendern if modus == "llm" else aenderung.anwenden)(vorher, fall["text"])
        soll, ist = als_menge(fall["nachher"]), als_menge(nachher)
        if zeigen and soll != ist:
            print(f"  {fall['id']}: fehlt {dict(soll - ist)} | zu viel {dict(ist - soll)}")
        paare.append((soll, ist))
    return bewerten(paare)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--modus", choices=["regeln", "llm"], default="regeln")
    ap.add_argument("--fehler", action="store_true", help="Abweichungen je Fall anzeigen")
    args = ap.parse_args()
    for titel, fn, datei in [("Extraktion dev", extraktion, "dev.jsonl"), ("Extraktion holdout", extraktion, "holdout.jsonl"),
                             ("Extraktion stress", extraktion, "stress.jsonl"),
                             ("Änderungen dev", aenderungen, "aenderungen_dev.jsonl"),
                             ("Änderungen holdout", aenderungen, "aenderungen_holdout.jsonl")]:
        print(titel)
        e = fn(datei, args.modus, args.fehler)
        print(f"  Precision {e['precision']:.2f} | Recall {e['recall']:.2f} | F1 {e['f1']:.2f} | Fälle exakt {e['exakt']}")
