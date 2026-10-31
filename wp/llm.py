"""Sprachmodell mit strukturierter Ausgabe. Das Modell darf nur Komponenten und Räume aus dem Katalog wählen
(Pydantic-Schema); Preise, Summen und Prüfregeln rechnet der Code, nicht das Modell."""
import os

from wp.katalog import KOMPONENTEN, RAEUME
from wp.schema import Plan, Position, zusammenfassen

MODEL = "gpt-4o-mini"

KATALOG = "\n".join(f"- {k}: {v[0]}" for k, v in KOMPONENTEN.items())

SYSTEM = f"""Du hilfst einem Elektrobetrieb. Aus Notizen eines Kundengesprächs erstellst du Positionen für die Elektroplanung.
Räume (Schlüssel): {", ".join(RAEUME)}. Büro = arbeitszimmer.
Komponenten (Schlüssel: Bedeutung):
{KATALOG}
Regeln:
- Jede Leuchte an der Decke (Deckenlicht, Pendelleuchte, Einbaustrahler) ist ein deckenauslass, jede Leuchte an der Wand ein wandauslass.
- "dimmbar" heißt ein dimmer. Licht, das an zwei Stellen geschaltet wird, heißt zwei wechselschalter (bei Tastern zwei taster).
- "je eine ... links und rechts" sind zwei Stück.
- Gleiche Komponente im gleichen Raum zusammenzählen.
- Nur aufnehmen, was der Kunde wünscht. Nichts ergänzen, was nicht im Text steht.
- hinweis: Ort im Raum in den Worten des Textes, sonst leer.
- Unklares (fehlender Raum, fehlende Anzahl) als kurze Frage in offene_fragen."""

AENDERN = """Hier ist der aktuelle Plan als JSON und ein Änderungswunsch des Kunden.
Gib den vollständigen neuen Plan zurück. Alles, was der Wunsch nicht betrifft, bleibt unverändert.
Plan:
{plan}
Änderungswunsch: {text}"""


def available() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def _parse(user: str) -> Plan:
    from openai import OpenAI

    client = OpenAI(timeout=30, max_retries=2)
    response = client.chat.completions.parse(
        model=MODEL, temperature=0, response_format=Plan,
        messages=[{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}])
    return response.choices[0].message.parsed


def extrahieren(text: str) -> Plan:
    plan = _parse(text)
    return plan.model_copy(update={"positionen": zusammenfassen(plan.positionen)})


def aendern(plan: list[Position], text: str) -> list[Position]:
    alt = Plan(positionen=plan).model_dump_json(include={"positionen"})
    return zusammenfassen(_parse(AENDERN.format(plan=alt, text=text)).positionen)


def transkribieren(audio: bytes, dateiname: str = "notiz.wav") -> str:
    """Gesprochene Notizen zu Text (Deutsch)."""
    from openai import OpenAI

    client = OpenAI(timeout=60, max_retries=1)
    return client.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=(dateiname, audio), language="de").text
