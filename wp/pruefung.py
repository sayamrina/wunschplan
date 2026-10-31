"""Plausibilitätsprüfung im Code. Hinweise für die Fachkraft, keine Normprüfung und keine Rechtsberatung."""
from wp.katalog import RAEUME
from wp.schema import Position

# Rauchwarnmelder sind in allen Bundesländern für Schlafräume, Kinderzimmer und Flure (Rettungswege) vorgeschrieben.
RAUCHMELDER_PFLICHT = ("schlafzimmer", "kinderzimmer", "flur")
LICHT = ("deckenauslass", "wandauslass")
STECKDOSEN = ("steckdose", "doppelsteckdose", "dreifachsteckdose", "usb_steckdose", "aussensteckdose")


def pruefen(plan: list[Position]) -> list[tuple[str, str, tuple[str, list[tuple[str, str, int]]] | None]]:
    """Liste aus (Stufe, Text, Vorschlag). Stufe ist 'warnung' oder 'hinweis'; Vorschlag ist None oder
    (Beschriftung, [(Raum, Komponente, Änderung der Anzahl)]) und lässt sich mit einem Klick übernehmen."""
    out = []
    raeume = list(dict.fromkeys(p.raum for p in plan))
    for raum in raeume:
        im_raum = {p.komponente: p.anzahl for p in plan if p.raum == raum}
        name = RAEUME[raum]
        if raum in RAUCHMELDER_PFLICHT and "rauchmelder" not in im_raum:
            out.append(("warnung", f"{name}: kein Rauchwarnmelder geplant. Nach Landesbauordnung ist er hier Pflicht.",
                        ("Rauchmelder ergänzen", [(raum, "rauchmelder", 1)])))
        if im_raum.get("wechselschalter", 0) == 1:
            out.append(("warnung", f"{name}: Wechselschaltung braucht zwei Wechselschalter, geplant ist einer.",
                        ("Zweiten Wechselschalter ergänzen", [(raum, "wechselschalter", 1)])))
        if not any(k in im_raum for k in LICHT) and raum not in ("terrasse", "balkon"):
            out.append(("hinweis", f"{name}: kein Licht geplant. Beim Kunden nachfragen.",
                        ("Deckenauslass mit Schalter ergänzen", [(raum, "deckenauslass", 1), (raum, "ausschalter", 1)])))
        if any(k in im_raum for k in LICHT) and not any(
                k in im_raum for k in ("ausschalter", "wechselschalter", "serienschalter", "taster", "dimmer", "bewegungsmelder")):
            out.append(("hinweis", f"{name}: Licht ohne Schalter geplant. Schaltstelle klären.",
                        ("Ausschalter ergänzen", [(raum, "ausschalter", 1)])))
        if raum == "bad" and any(k in im_raum for k in STECKDOSEN):
            out.append(("hinweis", "Bad: Schutzbereiche nach DIN VDE 0100-701 beachten, Stromkreis mit Fehlerstromschutz (RCD).", None))
        if raum in ("terrasse", "balkon", "garage"):
            innen = [k for k in ("steckdose", "doppelsteckdose") if k in im_raum]
            if innen:
                n = sum(im_raum[k] for k in innen)
                out.append(("hinweis", f"{name}: im Außenbereich Außensteckdosen (IP44) statt Innensteckdosen prüfen.",
                            ("Durch Außensteckdosen ersetzen",
                             [(raum, k, -im_raum[k]) for k in innen] + [(raum, "aussensteckdose", n)])))
        if "herdanschluss" in im_raum:
            out.append(("hinweis", f"{name}: Herdanschluss braucht einen eigenen Stromkreis (400 V).", None))
    return out
