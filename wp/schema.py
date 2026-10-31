"""Datenmodell: ein Plan ist eine Liste von Positionen (Raum, Komponente, Anzahl, Hinweis)."""
from typing import Literal

from pydantic import BaseModel, Field

from wp.katalog import KOMPONENTEN, RAEUME

Raum = Literal[tuple(RAEUME)]
Komponente = Literal[tuple(KOMPONENTEN)]


class Position(BaseModel):
    raum: Raum
    komponente: Komponente
    anzahl: int = Field(ge=1, le=50)
    hinweis: str = Field(default="", description="Ort im Raum in den Worten des Kunden, z. B. 'neben dem Bett'")


class Plan(BaseModel):
    positionen: list[Position]
    offene_fragen: list[str] = Field(default_factory=list, description="Was im Text unklar ist und nachgefragt werden muss")


def zusammenfassen(positionen: list[Position]) -> list[Position]:
    """Gleiche Komponente im gleichen Raum wird zu einer Position addiert; Reihenfolge bleibt erhalten."""
    out: dict[tuple[str, str], Position] = {}
    for p in positionen:
        key = (p.raum, p.komponente)
        if key in out:
            alt = out[key]
            hinweis = "; ".join(h for h in (alt.hinweis, p.hinweis) if h)
            out[key] = alt.model_copy(update={"anzahl": alt.anzahl + p.anzahl, "hinweis": hinweis})
        else:
            out[key] = p
    return list(out.values())
