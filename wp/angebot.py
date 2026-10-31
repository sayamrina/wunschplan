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


def pdf(plan: list[Position], stundensatz: float, kunde: str, nummer: str, datum: str) -> bytes:
    """Angebot als PDF (A4) mit IBM Plex Sans. Beträge im Code berechnet wie in erstellen()."""
    from pathlib import Path

    from fpdf import FPDF

    fonts = Path(__file__).resolve().parent.parent / "assets" / "fonts"
    a = erstellen(plan, stundensatz)
    doc = FPDF(format="A4")
    doc.set_margins(20, 18, 20)
    doc.add_font("Plex", "", str(fonts / "IBMPlexSans-Regular.ttf"))
    doc.add_font("Plex", "B", str(fonts / "IBMPlexSans-SemiBold.ttf"))
    doc.add_page()
    doc.set_fill_color(253, 41, 80)
    doc.rect(0, 0, 210, 4, "F")
    doc.set_font("Plex", "B", 20)
    doc.cell(0, 12, f"Angebot {nummer}", new_x="LMARGIN", new_y="NEXT")
    doc.set_font("Plex", "", 10)
    doc.cell(0, 6, f"Kunde: {kunde}", new_x="LMARGIN", new_y="NEXT")
    doc.cell(0, 6, f"Datum: {datum}   |   Stundensatz Montage: {euro(stundensatz)} netto", new_x="LMARGIN", new_y="NEXT")
    doc.ln(4)
    breiten = (12, 14, 84, 30, 30)
    doc.set_font("Plex", "B", 9)
    doc.set_fill_color(241, 240, 238)
    for text, w, al in zip(("Pos.", "Menge", "Bezeichnung", "Einzelpreis", "Gesamt"), breiten, "LRLRR", strict=True):
        doc.cell(w, 8, text, border="B", align=al, fill=True)
    doc.ln()
    doc.set_font("Plex", "", 9)
    for i, z in enumerate(a["zeilen"], 1):
        y0 = doc.get_y()
        doc.cell(breiten[0], 6, str(i))
        doc.cell(breiten[1], 6, str(z["menge"]), align="R")
        x_text = doc.get_x()
        doc.multi_cell(breiten[2], 6, f"{z['position']}\nRäume: {z['raeume']}", new_x="RIGHT", new_y="TOP")
        doc.set_xy(x_text + breiten[2], y0)
        doc.cell(breiten[3], 6, euro(z["einzelpreis"]), align="R")
        doc.cell(breiten[4], 6, euro(z["gesamt"]), align="R")
        doc.set_y(y0 + 13)
        doc.set_draw_color(214, 212, 208)
        doc.line(20, doc.get_y() - 0.5, 190, doc.get_y() - 0.5)
    doc.ln(3)
    for label, wert, fett in (("Summe netto", a["netto"], False), ("MwSt. 19 %", a["mwst"], False), ("Gesamt brutto", a["brutto"], True)):
        doc.set_font("Plex", "B" if fett else "", 11 if fett else 10)
        doc.cell(140, 7, label, align="R")
        doc.cell(30, 7, euro(wert), align="R", new_x="LMARGIN", new_y="NEXT")
    doc.ln(8)
    doc.set_font("Plex", "", 8)
    doc.set_text_color(93, 108, 123)
    doc.multi_cell(0, 4.5, "Einzelpreis = Material + Montage (Minuten je Komponente × Stundensatz). Katalog und Preise sind "
                           "Beispielwerte aus einer Demo-Anwendung. Erstellt mit Wunschplan.", align="L")
    return bytes(doc.output())
