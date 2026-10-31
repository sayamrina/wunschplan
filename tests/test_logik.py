import pytest

import evaluieren
from wp import aenderung, angebot, grundriss, pruefung, regeln
from wp.schema import Position


def P(raum, komp, n=1):
    return Position(raum=raum, komponente=komp, anzahl=n)


@pytest.mark.parametrize("datei", ["dev.jsonl", "holdout.jsonl"])
def test_extraktion_regeln_bleibt_exakt(datei):
    assert evaluieren.extraktion(datei, "regeln", False)["f1"] == 1.0


@pytest.mark.parametrize("datei", ["aenderungen_dev.jsonl", "aenderungen_holdout.jsonl"])
def test_aenderungen_regeln_bleiben_exakt(datei):
    assert evaluieren.aenderungen(datei, "regeln", False)["f1"] == 1.0


def test_doppelsteckdose_zaehlt_nicht_als_steckdose():
    plan = regeln.extrahieren("Küche: zwei Doppelsteckdosen.").positionen
    assert [(p.komponente, p.anzahl) for p in plan] == [("doppelsteckdose", 2)]


def test_raum_als_ortsangabe_wechselt_den_raum_nicht():
    plan = regeln.extrahieren("Esszimmer: zwei Steckdosen an der Wand zur Küche.").positionen
    assert {p.raum for p in plan} == {"esszimmer"}


def test_ohne_raum_offene_frage_statt_position():
    plan = regeln.extrahieren("Zwei Steckdosen bitte.")
    assert plan.positionen == [] and plan.offene_fragen


def test_unverstaendliche_aenderung_laesst_plan_gleich():
    vorher = [P("bad", "steckdose")]
    assert aenderung.anwenden(vorher, "Bitte nochmal anrufen.") == vorher


def test_unterschied_zeigt_nur_geaenderte():
    d = aenderung.unterschied([P("bad", "steckdose"), P("bad", "deckenauslass")], [P("bad", "deckenauslass", 2)])
    assert [(x["komponente"], x["vorher"], x["nachher"]) for x in d] == [("steckdose", 1, 0), ("deckenauslass", 1, 2)]


def test_angebot_rechnet_material_montage_und_mwst():
    a = angebot.erstellen([P("bad", "steckdose", 2)], stundensatz=60.0)
    z = a["zeilen"][0]
    assert z["montage_stk"] == 25.0 and z["einzelpreis"] == 34.8 and z["gesamt"] == 69.6
    assert a["mwst"] == 13.22 and a["brutto"] == 82.82


def test_euro_format():
    assert angebot.euro(1234.5) == "1.234,50 €"


def test_pruefung_rauchmelder_und_wechselschaltung():
    texte = [t for _, t, _ in pruefung.pruefen([P("schlafzimmer", "wechselschalter"), P("schlafzimmer", "deckenauslass")])]
    assert any("Rauchwarnmelder" in t for t in texte)
    assert any("zwei Wechselschalter" in t for t in texte)


def test_grundriss_markiert_entfallene_komponente():
    svg = grundriss.zeichnen([P("flur", "taster", 2)], vorher=[P("flur", "wechselschalter", 2)])
    assert svg.startswith("<svg") and grundriss.WEG in svg and grundriss.NEU in svg


def test_angebot_pdf_ist_pdf():
    b = angebot.pdf([P("kueche", "herdanschluss"), P("flur", "rauchmelder")], 68.0, "Familie Beispiel", "WP-1", "01.11.2026")
    assert b[:4] == b"%PDF" and len(b) > 5000


def test_vorschlag_ersetzt_innensteckdosen_aussen():
    hinweise = pruefung.pruefen([P("garage", "steckdose", 2), P("garage", "deckenauslass"), P("garage", "ausschalter")])
    _, _, (_, schritte) = next(h for h in hinweise if h[2] and "Außensteckdosen" in h[2][0])
    plan = [P("garage", "steckdose", 2)]
    for raum, komp, delta in schritte:
        plan = aenderung.anpassen(plan, raum, komp, delta)
    assert [(p.komponente, p.anzahl) for p in plan] == [("aussensteckdose", 2)]
