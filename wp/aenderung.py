"""Änderungswünsche auf einen bestehenden Plan anwenden und den Unterschied berechnen."""
import re

from wp import regeln
from wp.katalog import RAEUME
from wp.schema import Position, zusammenfassen

ENTFERNEN_RE = re.compile(r"entfällt|entfallen|\bweg\b|streichen|gestrichen|\braus\b|nicht mehr|\bkein(?:e|en)?\b")
ANZAHL_STATT_RE = re.compile(r"\b(\d{1,2}|[a-zäöüß]+)\s+statt\s+(\d{1,2}|[a-zäöüß]+)\b")
NUR_RE = re.compile(r"\bnur\s+(?:noch\s+)?(\d{1,2}|[a-zäöüß]+)\b")


def _raum(text: str, plan: list[Position]) -> str | None:
    raeume = regeln.raeume_im_text(text)
    if raeume:
        return raeume[0][1]
    im_plan = {p.raum for p in plan}
    return im_plan.pop() if len(im_plan) == 1 else None


def _setzen(plan: list[Position], raum: str, komp: str, anzahl: int) -> list[Position]:
    rest = [p for p in plan if not (p.raum == raum and p.komponente == komp)]
    if anzahl <= 0:
        return rest
    alt = next((p for p in plan if p.raum == raum and p.komponente == komp), None)
    if alt:  # Position an ihrer Stelle lassen
        return [p.model_copy(update={"anzahl": anzahl}) if p is alt else p for p in plan]
    return rest + [Position(raum=raum, komponente=komp, anzahl=anzahl)]


def anwenden(plan: list[Position], text: str) -> list[Position]:
    """Regelbasiert: ersetzen ('statt X lieber Y', 'X durch Y ersetzen'), Anzahl ändern ('sechs statt vier'),
    entfernen ('entfällt', 'streichen') oder hinzufügen (alles andere)."""
    t = text.lower()
    raum = _raum(t, plan)
    if raum is None:
        return plan
    nennungen = regeln.komponenten_im_text(t)
    if not nennungen:
        return plan

    m = ANZAHL_STATT_RE.search(t)
    if m and all(regeln.ZAHL_RE.fullmatch(g) for g in m.groups()):
        komp = next(k for n, k in nennungen if n.start() > m.end() - 1)
        return _setzen(plan, raum, komp, regeln.zahl(m.group(1)))

    m = NUR_RE.search(t)
    if m and regeln.ZAHL_RE.fullmatch(m.group(1)) and len(nennungen) == 1:
        return _setzen(plan, raum, nennungen[0][1], regeln.zahl(m.group(1)))

    ersetzen = re.search(r"\bstatt\b", t) or re.search(r"\bdurch\b.*\bersetz", t)
    if ersetzen and len(nennungen) >= 2:
        if "statt" in ersetzen.group(0):
            alt = next(k for n, k in nennungen if n.start() > ersetzen.start())
            neu_m, neu = next((n, k) for n, k in nennungen if k != alt)
        else:
            alt, (neu_m, neu) = nennungen[0][1], nennungen[1]
        anzahl = regeln.anzahl_vor(t, neu_m.start()) or next(
            (p.anzahl for p in plan if p.raum == raum and p.komponente == alt), 1)
        if re.search(r"\b(?:zweite|weitere|zusätzliche|noch)\b", " ".join(t[:neu_m.start()].split()[-3:])):
            anzahl += next((p.anzahl for p in plan if p.raum == raum and p.komponente == neu), 0)  # "eine zweite ..."
        return _setzen(_setzen(plan, raum, alt, 0), raum, neu, anzahl)

    if ENTFERNEN_RE.search(t):
        for _, komp in nennungen:
            plan = _setzen(plan, raum, komp, 0)
        return plan

    neu = regeln.extrahieren(text, start_raum=raum).positionen
    return zusammenfassen(plan + neu)


def unterschied(vorher: list[Position], nachher: list[Position]) -> list[dict]:
    """Je (Raum, Komponente) die Anzahl vorher und nachher, nur wo sich etwas geändert hat."""
    def zaehlen(plan):
        out = {}
        for p in plan:
            out[(p.raum, p.komponente)] = out.get((p.raum, p.komponente), 0) + p.anzahl
        return out
    a, b = zaehlen(vorher), zaehlen(nachher)
    reihen = []
    for key in list(a) + [k for k in b if k not in a]:
        if a.get(key, 0) != b.get(key, 0):
            reihen.append({"raum": RAEUME[key[0]], "komponente": key[1], "vorher": a.get(key, 0), "nachher": b.get(key, 0)})
    return reihen
