"""Angebot aus dem Plan: Material und Montage je Komponente, Summen mit Mehrwertsteuer. Alles im Code gerechnet."""
from wp.katalog import KOMPONENTEN, MWST, RAEUME, STUNDENSATZ
from wp.schema import Position


def erstellen(plan: list[Position], stundensatz: float = STUNDENSATZ) -> dict:
    zeilen = {}
    for p in plan:
        name, material, minuten, _ = KOMPONENTEN[p.komponente]
        z = zeilen.setdefault(p.komponente, {"position": name, "menge": 0, "raeume": [], "material_stk": material,
                                             "montage_stk": round(minuten / 60 * stundensatz, 2)})
        z["menge"] += p.anzahl
        z["raeume"].append(RAEUME[p.raum])
    for z in zeilen.values():
        z["raeume"] = ", ".join(dict.fromkeys(z["raeume"]))
        z["einzelpreis"] = round(z["material_stk"] + z["montage_stk"], 2)
        z["gesamt"] = round(z["einzelpreis"] * z["menge"], 2)
    netto = round(sum(z["gesamt"] for z in zeilen.values()), 2)
    mwst = round(netto * MWST, 2)
    return {"zeilen": list(zeilen.values()), "netto": netto, "mwst": mwst, "brutto": round(netto + mwst, 2)}


def euro(betrag: float) -> str:
    return f"{betrag:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
