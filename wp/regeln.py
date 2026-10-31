"""Regelbasierte Erkennung (Offline-Modus): findet Räume, Komponenten und Anzahlen in deutschen Notizen."""
import re

from wp.schema import Plan, Position, zusammenfassen

RAUM_MUSTER = {
    "schlafzimmer": r"schlafzimmer|schlafraum",
    "kinderzimmer": r"kinderzimmer",
    "wohnzimmer": r"wohnzimmer|wohnbereich",
    "arbeitszimmer": r"arbeitszimmer|büro|homeoffice",
    "esszimmer": r"esszimmer|essbereich",
    "kueche": r"küche",
    "bad": r"\bbad(?:ezimmer)?\b",
    "gaeste_wc": r"gäste-?\s?wc|\bwc\b",
    "flur": r"\bflur|\bdiele",
    "abstellraum": r"abstellraum",
    "hauswirtschaftsraum": r"hauswirtschaftsraum|\bhwr\b",
    "keller": r"\bkeller",
    "garage": r"\bgarage",
    "terrasse": r"terrasse",
    "balkon": r"balkon",
}

# Reihenfolge ist wichtig: längere Begriffe zuerst, damit "Doppelsteckdose" nicht als "Steckdose" zählt.
KOMPONENTEN_MUSTER = [
    ("dreifachsteckdose", r"(?:dreifach|3-?fach)-?steckdosen?"),
    ("doppelsteckdose", r"(?:doppel|zweifach|2-?fach)-?steckdosen?"),
    ("usb_steckdose", r"usb-?steckdosen?"),
    ("aussensteckdose", r"au(?:ß|ss)en-?steckdosen?"),
    ("steckdose", r"steckdosen?"),
    ("herdanschluss", r"herd-?anschluss(?:dose)?"),
    ("wechselschalter", r"wechsel-?schalter(?:n)?|wechselschaltung"),
    ("serienschalter", r"serien-?schalter(?:n)?"),
    ("taster", r"\btaster(?:n)?\b"),
    ("dimmer", r"dimmer|dimmbar"),
    ("ausschalter", r"ausschalter(?:n)?|lichtschalter(?:n)?|\bschalter\b"),
    ("rauchmelder", r"rauch(?:warn)?melder(?:n)?"),
    ("bewegungsmelder", r"bewegungsmelder(?:n)?"),
    ("netzwerkdose", r"netzwerk-?(?:dosen?|anschl(?:uss|üsse))|lan-?(?:dosen?|anschl(?:uss|üsse))"),
    ("antennendose", r"antennen-?(?:dosen?|anschluss)|tv-?dosen?|sat-?dosen?"),
    ("wandauslass", r"wandleuchten?|spiegelleuchten?|außenleuchten?|wand-?auslass|wand-?auslässe"),
    ("deckenauslass", r"einbaustrahler(?:-auslässe)?|decken-?(?:leuchten?|licht|lampen?|auslass|auslässe)|pendelleuchten?|\blicht\b"),
]
KOMP_RE = re.compile("|".join(f"(?P<{k}>{m})" for k, m in KOMPONENTEN_MUSTER))

ZAHLWORTE = {"ein": 1, "eine": 1, "einen": 1, "einem": 1, "einer": 1, "zwei": 2, "drei": 3, "vier": 4, "fünf": 5,
             "sechs": 6, "sieben": 7, "acht": 8, "neun": 9, "zehn": 10, "elf": 11, "zwölf": 12}
ZAHL_RE = re.compile(r"\b(\d{1,2}|" + "|".join(ZAHLWORTE) + r")\b")
BEIDSEITIG_RE = re.compile(r"links und rechts|auf beiden seiten|beidseitig|an beiden enden|an beiden seiten")
ZWEI_STELLEN_RE = re.compile(r"\b(?:an|von|am|vom)\b[^.,;]{1,30}\bund\b\s+(?:an|von|am|vom)\b[^.,;]{1,30}\bschalt")
ORT_RE = re.compile(r"^\s*((?:neben|über|unter|hinter|vor|am|an der|an den|an|im|links|rechts|für|zur|zum)\b"
                    r"(?:(?!\s(?:und|mit)\b)[^.,;]){0,40})")  # Ortsangabe bis zum nächsten "und"/"mit"
# Ein Raum nach "zur/zum/neben der" ist eine Ortsangabe ("Wand zur Küche"), kein Raumwechsel.
ORTSBEZUG_RE = re.compile(r"(?:zur|zum|neben der|neben dem|richtung)\s+$")


def zahl(wort: str) -> int:
    return int(wort) if wort.isdigit() else ZAHLWORTE[wort]


def raeume_im_text(text: str) -> list[tuple[int, str]]:
    """(Position, Raum) aller Raumnennungen, die einen Raumwechsel bedeuten."""
    treffer = []
    for raum, muster in RAUM_MUSTER.items():
        for m in re.finditer(muster, text):
            if not ORTSBEZUG_RE.search(text[max(0, m.start() - 12):m.start()]):
                treffer.append((m.start(), raum))
    return sorted(treffer)


def komponenten_im_text(text: str) -> list[tuple[re.Match, str]]:
    return [(m, m.lastgroup) for m in KOMP_RE.finditer(text)]


def anzahl_vor(text: str, start: int) -> int | None:
    """Zahl in den drei Wörtern vor einer Nennung, z. B. 'zwei Doppelsteckdosen', '4 Steckdosen'."""
    davor = text[:start].split()[-3:]
    for wort in reversed(davor):
        wort = wort.strip(",:;()")
        if ZAHL_RE.fullmatch(wort):
            return zahl(wort)
    return None


def satzteil(text: str, pos: int) -> str:
    anfang = max(text.rfind(z, 0, pos) for z in ".;:\n") + 1
    ende = min([i for i in (text.find(z, pos) for z in ".;\n") if i != -1] or [len(text)])
    return text[anfang:ende]


def extrahieren(text: str, start_raum: str | None = None) -> Plan:
    t = text.lower()
    raeume = raeume_im_text(t)
    positionen, fragen = [], []
    for m, komp in komponenten_im_text(t):
        raum = start_raum
        for pos, r in raeume:
            if pos <= m.start():
                raum = r
        anzahl = anzahl_vor(t, m.start())
        teil = satzteil(t, m.start())
        davor = " ".join(t[:m.start()].split()[-3:])
        if anzahl is None:
            anzahl = 1
            if m.group(0).endswith(("dosen", "schaltern", "leuchten", "lampen", "auslässe")):
                fragen.append(f"Anzahl für '{m.group(0)}' nicht genannt: 1 angenommen, bitte prüfen.")
        if BEIDSEITIG_RE.search(teil) and re.search(r"\bje\b", davor):
            anzahl *= 2
        if komp == "taster" and BEIDSEITIG_RE.search(teil) and anzahl == 1:
            anzahl = 2
        if raum is None:
            fragen.append(f"Kein Raum erkennbar für '{m.group(0)}'.")
            continue
        ort = ORT_RE.match(t[m.end():])
        hinweis = text[m.end() + ort.start(1):m.end() + ort.end(1)].strip() if ort else ""  # Schreibweise des Originals
        positionen.append(Position(raum=raum, komponente=komp, anzahl=anzahl, hinweis=hinweis))
    # "an der Tür und am Bett schalten" heißt Wechselschaltung mit zwei Schaltern
    for m in ZWEI_STELLEN_RE.finditer(t):
        raum = start_raum
        for pos, r in raeume:
            if pos <= m.start():
                raum = r
        if raum and not any(p.raum == raum and p.komponente == "wechselschalter" for p in positionen):
            positionen.append(Position(raum=raum, komponente="wechselschalter", anzahl=2, hinweis="Wechselschaltung"))
    return Plan(positionen=zusammenfassen(positionen), offene_fragen=fragen)
