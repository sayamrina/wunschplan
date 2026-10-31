"""Komponenten, Räume und Beispielpreise. Die Preise sind erfunden und nur für die Demo gedacht."""

# Schlüssel: (Bezeichnung im Angebot, Materialpreis netto in €, Montage in Minuten, Kürzel im Grundriss)
KOMPONENTEN = {
    "steckdose": ("Schuko-Steckdose, einfach", 9.80, 25, "S"),
    "doppelsteckdose": ("Schuko-Steckdose, zweifach", 16.50, 30, "S2"),
    "dreifachsteckdose": ("Schuko-Steckdose, dreifach", 23.90, 35, "S3"),
    "usb_steckdose": ("Steckdose mit USB-A/C", 39.00, 30, "U"),
    "aussensteckdose": ("Außensteckdose IP44 mit Klappdeckel", 18.40, 40, "SA"),
    "herdanschluss": ("Herdanschlussdose 400 V", 12.60, 45, "H"),
    "ausschalter": ("Ausschalter", 11.20, 20, "A"),
    "wechselschalter": ("Wechselschalter", 12.90, 25, "W"),
    "serienschalter": ("Serienschalter", 15.70, 25, "SR"),
    "taster": ("Taster für Stromstoßschalter", 13.40, 25, "T"),
    "dimmer": ("Drehdimmer LED", 44.00, 30, "D"),
    "deckenauslass": ("Deckenauslass für Leuchte", 6.30, 30, "L"),
    "wandauslass": ("Wandauslass für Leuchte", 6.30, 30, "WL"),
    "netzwerkdose": ("Netzwerkdose Cat.6, zweifach", 24.50, 45, "N"),
    "antennendose": ("Antennendose TV/Radio", 14.80, 30, "TV"),
    "rauchmelder": ("Rauchwarnmelder, 10-Jahres-Batterie", 21.00, 15, "R"),
    "bewegungsmelder": ("Bewegungsmelder, Aufputz", 32.00, 30, "B"),
}

RAEUME = {
    "wohnzimmer": "Wohnzimmer",
    "schlafzimmer": "Schlafzimmer",
    "kinderzimmer": "Kinderzimmer",
    "arbeitszimmer": "Arbeitszimmer",
    "esszimmer": "Esszimmer",
    "kueche": "Küche",
    "bad": "Bad",
    "gaeste_wc": "Gäste-WC",
    "flur": "Flur",
    "abstellraum": "Abstellraum",
    "hauswirtschaftsraum": "Hauswirtschaftsraum",
    "keller": "Keller",
    "garage": "Garage",
    "terrasse": "Terrasse",
    "balkon": "Balkon",
}

STUNDENSATZ = 68.0  # € netto je Monteurstunde, Beispielwert
MWST = 0.19


def bezeichnung(komponente: str) -> str:
    return KOMPONENTEN[komponente][0]
