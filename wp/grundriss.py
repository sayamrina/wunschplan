"""Schematischer Installationsplan als SVG im Stil einer Bauzeichnung: Räume liegen aneinander, Wände sind schraffiert,
Symbole angelehnt an EN 60617. Steckdosen und Datendosen sitzen an der unteren Wand, Schalter an der linken Wand
neben der Tür, Wandleuchten an der rechten Wand, Deckenleuchten in der Raummitte, Melder unter der Decke.
Die Lage ist schematisch; der echte Grundriss entsteht in der Planungssoftware."""
from html import escape

from wp.katalog import KOMPONENTEN, RAEUME
from wp.schema import Position

TINTE, NEU, WEG, RAUM = "#17171C", "#12A150", "#FD2950", "#FFFFFF"
BREITE, AUSSEN, INNEN, MAX_SYMBOLE = 960, 14, 9, 8

UNTEN = ("steckdose", "doppelsteckdose", "dreifachsteckdose", "usb_steckdose", "aussensteckdose", "herdanschluss",
         "netzwerkdose", "antennendose")
LINKS = ("ausschalter", "wechselschalter", "serienschalter", "taster", "dimmer")
RECHTS = ("wandauslass",)
MITTE = ("deckenauslass",)
OBEN = ("rauchmelder", "bewegungsmelder")


def _symbol(komp: str, x: float, y: float, farbe: str) -> str:
    s = f'stroke="{farbe}" stroke-width="2" fill="{RAUM}" stroke-linecap="round"'
    if komp in ("netzwerkdose", "antennendose"):
        k = KOMPONENTEN[komp][3]
        return (f'<rect x="{x-11}" y="{y-20}" width="22" height="20" {s}/>'
                f'<text x="{x}" y="{y-6}" text-anchor="middle" font-size="10" font-weight="600" fill="{farbe}">{k}</text>')
    if komp in UNTEN:  # Halbkreis auf der Wand, Schutzkontakt als Strich, Mehrfachdosen mit Strichen
        out = f'<path d="M{x-11},{y} A11,11 0 0 1 {x+11},{y} Z" {s}/><line x1="{x}" y1="{y-11}" x2="{x}" y2="{y-18}" {s}/>'
        striche = {"doppelsteckdose": 2, "dreifachsteckdose": 3}.get(komp, 0)
        for i in range(striche):
            dx = (i - (striche - 1) / 2) * 5
            out += f'<line x1="{x+dx+7}" y1="{y-20}" x2="{x+dx+10}" y2="{y-25}" {s}/>'
        if komp == "herdanschluss":
            out += f'<line x1="{x-6}" y1="{y-15}" x2="{x+6}" y2="{y-15}" {s}/>'
        if komp in ("usb_steckdose", "aussensteckdose"):
            out += (f'<text x="{x}" y="{y-2}" text-anchor="middle" font-size="7.5" font-weight="600" fill="{farbe}">'
                    f'{"USB" if komp == "usb_steckdose" else "IP"}</text>')
        return out
    if komp in LINKS:  # Kreis an der Wand mit Schaltstrich in den Raum
        out = f'<circle cx="{x}" cy="{y}" r="5.5" {s}/><line x1="{x+4}" y1="{y-4}" x2="{x+14}" y2="{y-12}" {s}/>'
        if komp in ("wechselschalter", "serienschalter"):
            out += f'<line x1="{x+4}" y1="{y+4}" x2="{x+14}" y2="{y+12}" {s}/>'
        if komp == "taster":
            out += f'<circle cx="{x}" cy="{y}" r="2" fill="{farbe}"/>'
        if komp == "dimmer":
            out += f'<path d="M{x+16},{y-6} l5,0 l-2.5,5 z" fill="{farbe}"/>'
        return out
    if komp in OBEN:
        k = KOMPONENTEN[komp][3]
        return (f'<circle cx="{x}" cy="{y}" r="10" {s}/>'
                f'<text x="{x}" y="{y+3.5}" text-anchor="middle" font-size="10" font-weight="600" fill="{farbe}">{k}</text>')
    d = 7  # Leuchte: Kreis mit Kreuz
    return (f'<circle cx="{x}" cy="{y}" r="10" {s}/><line x1="{x-d}" y1="{y-d}" x2="{x+d}" y2="{y+d}" {s}/>'
            f'<line x1="{x-d}" y1="{y+d}" x2="{x+d}" y2="{y-d}" {s}/>')


def _stuecke(eintraege: list[tuple[str, int, int]], gruppe: tuple) -> list[tuple[str, str]]:
    """Einzelne Symbole mit Farbe: unverändert Tinte, dazugekommen grün, entfallen rot."""
    out = []
    for komp, alt, neu in eintraege:
        if komp not in gruppe:
            continue
        for i in range(min(max(alt, neu), MAX_SYMBOLE)):
            out.append((komp, TINTE if i < min(alt, neu) else NEU if neu > alt else WEG))
    return out


def _zeilen(raeume: list[dict]) -> list[list[dict]]:
    zeilen, aktuell, breite = [], [], 0
    for r in raeume:
        if aktuell and breite + r["min_b"] > BREITE - 2 * AUSSEN:
            zeilen.append(aktuell)
            aktuell, breite = [], 0
        aktuell.append(r)
        breite += r["min_b"] + INNEN
    return zeilen + [aktuell] if aktuell else zeilen


def zeichnen(plan: list[Position], vorher: list[Position] | None = None) -> str:
    """SVG des Plans. Mit 'vorher' werden neue Komponenten grün, entfallene rot gestrichelt gezeigt."""
    jetzt = {(p.raum, p.komponente): p.anzahl for p in plan}
    alt = {(p.raum, p.komponente): p.anzahl for p in vorher} if vorher is not None else dict(jetzt)
    schluessel = list(dict.fromkeys([*jetzt, *alt]))
    raeume = []
    for raum in [r for r in RAEUME if any(k[0] == r for k in schluessel)]:
        e = [(k[1], alt.get(k, 0), jetzt.get(k, 0)) for k in schluessel if k[0] == raum]
        unten, links = _stuecke(e, UNTEN), _stuecke(e, LINKS)
        raeume.append({"raum": raum, "e": e, "unten": unten, "links": links, "rechts": _stuecke(e, RECHTS),
                       "mitte": _stuecke(e, MITTE), "oben": _stuecke(e, OBEN),
                       "min_b": max(200, 70 + len(unten) * 34), "min_h": max(160, 70 + len(links) * 30)})
    if not raeume:
        return ""

    teile, y = [], AUSSEN
    for zeile in _zeilen(raeume):
        frei = BREITE - 2 * AUSSEN - INNEN * (len(zeile) - 1)
        summe = sum(r["min_b"] for r in zeile)
        h = max(r["min_h"] for r in zeile)
        x = AUSSEN
        for r in zeile:
            b = r["min_b"] / summe * frei
            teile.append(_raum(r, x, y, b, h))
            x += b + INNEN
        y += h + INNEN
    hoehe = y - INNEN + AUSSEN
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {BREITE} {hoehe}" width="100%" role="img" '
            f'aria-label="Schematischer Installationsplan" font-family="IBM Plex Sans, Arial, sans-serif">'
            '<defs><pattern id="schraffur" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="7" height="7" fill="#FFFFFF"/><line x1="0" y1="0" x2="0" y2="7" stroke="{TINTE}" stroke-width="1.6"/>'
            '</pattern></defs>'
            f'<rect x="0" y="0" width="{BREITE}" height="{hoehe}" fill="url(#schraffur)" stroke="{TINTE}" stroke-width="2"/>'
            + "".join(teile) + "</svg>")


def _raum(r: dict, x: float, y: float, b: float, h: float) -> str:
    name = escape(RAEUME[r["raum"]])
    out = [f'<rect x="{x}" y="{y}" width="{b}" height="{h}" fill="{RAUM}" stroke="{TINTE}" stroke-width="1.5"/>']
    # Tür in der oberen Wand mit Schwenkbogen
    tx, tw = x + 16, 34
    out.append(f'<rect x="{tx}" y="{y - INNEN - 1}" width="{tw}" height="{INNEN + 2}" fill="{RAUM}"/>'
               f'<path d="M{tx},{y} L{tx},{y + tw} A{tw},{tw} 0 0 0 {tx + tw},{y}" fill="none" stroke="{TINTE}" '
               f'stroke-width="1" stroke-dasharray="2 2"/>')
    out.append(f'<text x="{tx + tw + 12}" y="{y + 24}" font-size="15" font-weight="600" fill="{TINTE}">{name}</text>')

    def gruppe(stuecke, punkte):
        g = []
        for (komp, farbe), (px, py) in zip(stuecke, punkte, strict=False):
            sym = _symbol(komp, px, py, farbe)
            if farbe == WEG:
                sym = f'<g stroke-dasharray="3 2">{sym}</g>'
            g.append(f'<g><title>{escape(KOMPONENTEN[komp][0])}</title>{sym}</g>')
        return g

    n = len(r["unten"])
    schritt = (b - 60) / max(n, 1)
    sym = gruppe(r["unten"], [(x + 44 + i * schritt + schritt / 2 - 14, y + h) for i in range(n)])
    sym += gruppe(r["links"], [(x, y + h - 30 - i * 30) for i in range(len(r["links"]))])
    sym += gruppe(r["rechts"], [(x + b - 12, y + 60 + i * 32) for i in range(len(r["rechts"]))])
    m = len(r["mitte"])
    sym += gruppe(r["mitte"], [(x + b / 2 + (i - (m - 1) / 2) * 30, y + h / 2 + 4) for i in range(m)])
    sym += gruppe(r["oben"], [(x + b - 22 - i * 26, y + 22) for i in range(len(r["oben"]))])
    out.append(f'<g class="symbole" data-raum="{r["raum"]}">{"".join(sym)}</g>')  # je Raum gruppiert, z. B. für Animationen
    ueber = [f"{escape(KOMPONENTEN[k][0])} ×{max(a, n_)}" for k, a, n_ in r["e"] if max(a, n_) > MAX_SYMBOLE]
    if ueber:
        out.append(f'<text x="{x + 14}" y="{y + h - 40}" font-size="11" fill="{TINTE}">{"; ".join(ueber)}</text>')
    return "".join(out)


def legende() -> str:
    """Kleine Symbole mit Beschriftung, gleiche Zeichnung wie im Plan."""
    eintraege = [("steckdose", TINTE, "Steckdose"), ("doppelsteckdose", TINTE, "zweifach"), ("ausschalter", TINTE, "Schalter"),
                 ("wechselschalter", TINTE, "Wechselschalter"), ("deckenauslass", TINTE, "Leuchte"),
                 ("netzwerkdose", TINTE, "Datendose"), ("rauchmelder", TINTE, "Melder"),
                 ("steckdose", NEU, "neu"), ("steckdose", WEG, "entfällt")]
    teile = []
    for komp, farbe, text in eintraege:
        y = 26 if komp in UNTEN else 16
        sym = _symbol(komp, 18, y, farbe)
        if farbe == WEG:
            sym = f'<g stroke-dasharray="3 2">{sym}</g>'
        teile.append(f'<span class="leg"><svg width="38" height="30" viewBox="0 0 38 30" aria-hidden="true">{sym}</svg>{text}</span>')
    return "".join(teile)
