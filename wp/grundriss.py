"""Schematischer Installationsplan als SVG: ein Kasten je Raum, Symbole angelehnt an EN 60617.
Die Lage im Raum ist schematisch; der echte Grundriss entsteht in der Planungssoftware."""
from html import escape

from wp.katalog import KOMPONENTEN, RAEUME
from wp.schema import Position

GRAPHIT, KABEL, NEU, WEG, PUTZ = "#26292B", "#1F5FAD", "#2F7D32", "#B3261E", "#ECECE8"
ZELLE_B, SYM_B, SYM_H, PRO_REIHE, SPALTEN = 250, 46, 58, 5, 3

STECKDOSEN = {"steckdose", "doppelsteckdose", "dreifachsteckdose", "usb_steckdose", "aussensteckdose", "herdanschluss"}
SCHALTER = {"ausschalter", "wechselschalter", "serienschalter", "taster", "dimmer"}
LEUCHTEN = {"deckenauslass", "wandauslass"}


def _symbol(komp: str, x: float, y: float, farbe: str) -> str:
    s = f'stroke="{farbe}" stroke-width="1.8" fill="none"'
    if komp in STECKDOSEN:  # Halbkreis auf der Wandlinie, Schutzkontakt als Strich
        out = f'<path d="M{x-10},{y+6} A10,10 0 0 1 {x+10},{y+6} Z" {s}/><line x1="{x}" y1="{y-4}" x2="{x}" y2="{y-10}" {s}/>'
        if komp == "herdanschluss":
            out += f'<line x1="{x-6}" y1="{y-8}" x2="{x+6}" y2="{y-8}" {s}/>'
        return out
    if komp in SCHALTER:  # Kreis mit Schaltstrich
        out = f'<circle cx="{x}" cy="{y}" r="5" {s}/><line x1="{x+3.5}" y1="{y-3.5}" x2="{x+11}" y2="{y-11}" {s}/>'
        if komp in ("wechselschalter", "serienschalter"):
            out += f'<line x1="{x-3.5}" y1="{y+3.5}" x2="{x-11}" y2="{y+11}" {s}/>'
        return out
    if komp in LEUCHTEN:  # Kreis mit Kreuz
        d = 7
        return (f'<circle cx="{x}" cy="{y}" r="10" {s}/><line x1="{x-d}" y1="{y-d}" x2="{x+d}" y2="{y+d}" {s}/>'
                f'<line x1="{x-d}" y1="{y+d}" x2="{x+d}" y2="{y-d}" {s}/>')
    kuerzel = KOMPONENTEN[komp][3]
    return (f'<rect x="{x-10}" y="{y-10}" width="20" height="20" {s}/>'
            f'<text x="{x}" y="{y+4}" text-anchor="middle" font-size="10" fill="{farbe}" font-weight="600">{kuerzel}</text>')


def zeichnen(plan: list[Position], vorher: list[Position] | None = None) -> str:
    """SVG des Plans. Mit 'vorher' werden neue Komponenten grün, entfallene rot gestrichelt gezeigt."""
    jetzt = {(p.raum, p.komponente): p.anzahl for p in plan}
    alt = {(p.raum, p.komponente): p.anzahl for p in (vorher or [])} if vorher is not None else dict(jetzt)
    schluessel = list(dict.fromkeys([*jetzt, *alt]))
    raeume = [r for r in RAEUME if any(k[0] == r for k in schluessel)]
    if not raeume:
        return ""
    zellen, y_spalte = [], [0.0] * SPALTEN
    for i, raum in enumerate(raeume):
        sp = i % SPALTEN if len(raeume) >= SPALTEN else i
        eintraege = [k for k in schluessel if k[0] == raum]
        reihen = (len(eintraege) + PRO_REIHE - 1) // PRO_REIHE
        h = 44 + reihen * SYM_H
        x0, y0 = sp * (ZELLE_B + 14), y_spalte[sp]
        teile = [f'<rect x="{x0+2}" y="{y0+2}" width="{ZELLE_B-4}" height="{h-4}" fill="{PUTZ}" stroke="{GRAPHIT}" stroke-width="4"/>',
                 f'<text x="{x0+14}" y="{y0+26}" font-size="16" font-weight="600" fill="{GRAPHIT}">{escape(RAEUME[raum])}</text>']
        for j, key in enumerate(eintraege):
            n_neu, n_alt = jetzt.get(key, 0), alt.get(key, 0)
            farbe = WEG if n_neu == 0 else NEU if n_neu > n_alt else KABEL
            cx = x0 + 32 + (j % PRO_REIHE) * SYM_B
            cy = y0 + 62 + (j // PRO_REIHE) * SYM_H
            g = _symbol(key[1], cx, cy, farbe)
            if n_neu == 0:
                g = f'<g opacity="0.75" stroke-dasharray="3 2">{g}</g>'
            label = f"{n_alt}→{n_neu}" if n_neu != n_alt and n_alt else f"×{max(n_neu, n_alt)}"
            name = escape(KOMPONENTEN[key[1]][0])
            teile.append(f'<g><title>{name}: {label}</title>{g}'
                         f'<text x="{cx}" y="{cy+26}" text-anchor="middle" font-size="13" fill="{farbe}">{label}</text></g>')
        zellen.append("".join(teile))
        y_spalte[sp] += h + 14
    breite = min(len(raeume), SPALTEN) * (ZELLE_B + 14) - 14
    hoehe = max(y_spalte) - 14
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {breite} {hoehe}" width="100%" role="img" '
            f'aria-label="Schematischer Installationsplan" font-family="Barlow Condensed, Arial Narrow, sans-serif">'
            + "".join(zellen) + "</svg>")
