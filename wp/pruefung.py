"""Plausibilitätsprüfung im Code. Hinweise für die Fachkraft, keine Normprüfung und keine Rechtsberatung."""
from wp.katalog import RAEUME
from wp.schema import Position

# Rauchwarnmelder sind in allen Bundesländern für Schlafräume, Kinderzimmer und Flure (Rettungswege) vorgeschrieben.
RAUCHMELDER_PFLICHT = ("schlafzimmer", "kinderzimmer", "flur")
LICHT = ("deckenauslass", "wandauslass")
STECKDOSEN = ("steckdose", "doppelsteckdose", "dreifachsteckdose", "usb_steckdose", "aussensteckdose")


def pruefen(plan: list[Position]) -> list[tuple[str, str]]:
    """Liste aus (Stufe, Text); Stufe ist 'warnung' oder 'hinweis'."""
    out = []
    raeume = list(dict.fromkeys(p.raum for p in plan))
    for raum in raeume:
        im_raum = {p.komponente: p.anzahl for p in plan if p.raum == raum}
        name = RAEUME[raum]
        if raum in RAUCHMELDER_PFLICHT and "rauchmelder" not in im_raum:
            out.append(("warnung", f"{name}: kein Rauchwarnmelder geplant. Nach Landesbauordnung ist er hier Pflicht."))
        if im_raum.get("wechselschalter", 0) == 1:
            out.append(("warnung", f"{name}: Wechselschaltung braucht zwei Wechselschalter, geplant ist einer."))
        if not any(k in im_raum for k in LICHT) and raum not in ("terrasse", "balkon"):
            out.append(("hinweis", f"{name}: kein Licht geplant. Beim Kunden nachfragen."))
        if any(k in im_raum for k in LICHT) and not any(
                k in im_raum for k in ("ausschalter", "wechselschalter", "serienschalter", "taster", "dimmer", "bewegungsmelder")):
            out.append(("hinweis", f"{name}: Licht ohne Schalter geplant. Schaltstelle klären."))
        if raum == "bad" and any(k in im_raum for k in STECKDOSEN):
            out.append(("hinweis", "Bad: Schutzbereiche nach DIN VDE 0100-701 beachten, Stromkreis mit Fehlerstromschutz (RCD)."))
        if raum in ("terrasse", "balkon", "garage") and any(k in im_raum for k in ("steckdose", "doppelsteckdose")):
            out.append(("hinweis", f"{name}: im Außenbereich Außensteckdosen (IP44) statt Innensteckdosen prüfen."))
        if "herdanschluss" in im_raum:
            out.append(("hinweis", f"{name}: Herdanschluss braucht einen eigenen Stromkreis (400 V)."))
    return out
