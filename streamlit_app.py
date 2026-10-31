"""Wunschplan: aus Notizen eines Kundengesprächs werden Positionen, ein Installationsplan und ein Angebot."""
import os

import pandas as pd
import streamlit as st

from wp import aenderung, angebot, grundriss, llm, pruefung, regeln
from wp.katalog import KOMPONENTEN, RAEUME, STUNDENSATZ
from wp.schema import Position

try:  # Schlüssel aus den Streamlit-Secrets, falls gesetzt
    os.environ.setdefault("OPENAI_API_KEY", st.secrets["OPENAI_API_KEY"])
except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    pass

MAX_KI_AUFRUFE = 20

BEISPIELE = {
    "Einfamilienhaus, Erdgeschoss": (
        "Wohnzimmer: zwei Doppelsteckdosen am Sofa, an der TV-Wand eine Dreifachsteckdose, eine Netzwerkdose und eine "
        "Antennendose. Deckenlicht dimmbar.\n"
        "Küche mit Herdanschluss, sechs Steckdosen über der Arbeitsplatte und zwei Einbaustrahler-Auslässe an der Decke, "
        "dazu ein Lichtschalter an der Tür.\n"
        "Flur: Licht über Taster an beiden Enden und eine Steckdose für den Staubsauger.\n"
        "Gäste-WC nur eine Deckenleuchte mit Schalter.\n"
        "Auf der Terrasse eine Außensteckdose und eine Wandleuchte mit Bewegungsmelder."),
    "Schlafbereich, Obergeschoss": (
        "Im Schlafzimmer links und rechts vom Bett je eine Doppelsteckdose, dazu eine Deckenleuchte, die man an der Tür "
        "und am Bett schalten kann.\n"
        "Kinderzimmer bekommt einen Rauchmelder, zwei Doppelsteckdosen und eine Netzwerkdose am Schreibtisch.\n"
        "Bad mit Spiegelleuchte über dem Waschbecken, Deckenlicht mit Schalter und einer Doppelsteckdose neben dem Spiegel."),
    "Eigene Notiz": "",
}
AENDERUNG_BEISPIEL = "Im Wohnzimmer statt der Antennendose lieber eine zweite Netzwerkdose."

KOMP_NAME = {k: v[0] for k, v in KOMPONENTEN.items()}
KOMP_KEY = {v: k for k, v in KOMP_NAME.items()}
RAUM_KEY = {v: k for k, v in RAEUME.items()}

st.set_page_config(page_title="Wunschplan", page_icon="🔌", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@500;600;700&family=Barlow:wght@400;500;600&display=swap');
:root { --putz:#D9DAD5; --graphit:#26292B; --kabel:#1F5FAD; }
.stApp { background: var(--putz); color: var(--graphit); font-family: 'Barlow', sans-serif; }
h1, h2, h3, .raum { font-family: 'Barlow Condensed', sans-serif !important; letter-spacing: .01em; color: var(--graphit); }
h1 { font-size: 3.2rem !important; font-weight: 700 !important; line-height: 1 !important; margin-bottom: .2rem !important; }
.portfolio-banner { background: var(--graphit); color: #F2F2EF; padding: .55rem .9rem; font-size: .92rem; margin-bottom: 1.2rem; }
.portfolio-banner a { color: #9EC3F0; }
.unterzeile { font-size: 1.15rem; max-width: 46rem; margin-bottom: 1.4rem; }
.schritt { font-family: 'Barlow Condensed', sans-serif; font-size: 1.6rem; font-weight: 600; border-left: 6px solid var(--kabel);
           padding-left: .6rem; margin: 1.6rem 0 .6rem; }
.plan { background: #F4F4F1; padding: 14px; border: 1px solid #B9BBB5; overflow-x: auto; }
.plan svg { min-width: 720px; }
.legende { font-size: .85rem; margin-top: .4rem; }
.legende b { color: #2F7D32; } .legende i { color: #B3261E; font-style: normal; font-weight: 600; }
</style>""", unsafe_allow_html=True)

st.markdown('<div class="portfolio-banner">This app was developed by Amrina as part of a portfolio. '
            '<a href="https://sayamrina.github.io/" target="_blank" rel="noopener">View the portfolio →</a></div>',
            unsafe_allow_html=True)
st.title("Wunschplan")
st.markdown('<p class="unterzeile">Notizen aus dem Kundengespräch eingeben. Daraus entstehen Positionen, ein schematischer '
            'Installationsplan und ein Angebot. Änderungswünsche des Kunden werden als neue Version eingetragen und mit der '
            'vorherigen verglichen.</p>', unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("versionen", [])  # Liste aus (Beschreibung, [Position])
ss.setdefault("fragen", [])
ss.setdefault("ki_aufrufe", 0)

with st.sidebar:
    st.header("Einstellungen")
    ki_moeglich = llm.available() and ss.ki_aufrufe < MAX_KI_AUFRUFE
    optionen = ["Sprachmodell (gpt-4o-mini)", "Regeln (offline)"] if ki_moeglich else ["Regeln (offline)"]
    modus = st.radio("Erkennung", optionen)
    if not llm.available():
        st.caption("Kein API-Schlüssel hinterlegt: die App arbeitet mit Regeln. Für freie, unordentliche Notizen ist das "
                   "Sprachmodell deutlich besser (siehe Auswertung im README).")
    elif not ki_moeglich:
        st.caption(f"Maximal {MAX_KI_AUFRUFE} Modellaufrufe pro Besuch erreicht: weiter mit Regeln.")
    stundensatz = st.number_input("Stundensatz Monteur (€ netto)", 30.0, 150.0, STUNDENSATZ, 1.0)
    st.caption("Preise im Katalog sind Beispielwerte.")
ki = modus.startswith("Sprachmodell")


def ki_zaehlen():
    ss.ki_aufrufe += 1


st.markdown('<div class="schritt">1 Kundenwünsche</div>', unsafe_allow_html=True)
beispiel = st.selectbox("Beispiel", list(BEISPIELE))
notiz = st.text_area("Notizen aus dem Gespräch", BEISPIELE[beispiel], height=170, key=f"notiz_{beispiel}",
                     placeholder="z. B. Im Schlafzimmer links und rechts vom Bett je eine Doppelsteckdose …")
if st.button("Plan erstellen", type="primary", disabled=not notiz.strip()):
    with st.spinner("Notizen werden ausgewertet …"):
        try:
            plan = llm.extrahieren(notiz) if ki else regeln.extrahieren(notiz)
            if ki:
                ki_zaehlen()
        except Exception as e:  # Modell nicht erreichbar: mit Regeln weiterarbeiten
            st.warning(f"Sprachmodell nicht erreichbar ({type(e).__name__}). Der Plan wurde mit Regeln erstellt.")
            plan = regeln.extrahieren(notiz)
    ss.versionen = [("Erster Entwurf", plan.positionen)]
    ss.fragen = plan.offene_fragen

if not ss.versionen:
    st.info("Noch kein Plan. Wählen Sie ein Beispiel oder geben Sie eigene Notizen ein und klicken Sie auf „Plan erstellen“.")
    st.stop()

aktuell = ss.versionen[-1][1]
vorher = ss.versionen[-2][1] if len(ss.versionen) > 1 else None

st.markdown(f'<div class="schritt">2 Plan, Version {len(ss.versionen)}: {ss.versionen[-1][0]}</div>', unsafe_allow_html=True)
st.markdown(f'<div class="plan">{grundriss.zeichnen(aktuell, vorher)}</div>', unsafe_allow_html=True)
st.markdown('<div class="legende">Halbkreis Steckdose, Kreis mit Strich Schalter, Kreis mit Kreuz Leuchte, Quadrat sonstige '
            '(Kürzel). Seit der letzten Version <b>neu oder mehr</b>, <i>entfallen</i>. Lage im Raum schematisch.</div>',
            unsafe_allow_html=True)
links, rechts = st.columns(2, gap="large")
with links:
    st.subheader("Prüfung")
    hinweise = pruefung.pruefen(aktuell)
    for stufe, text in hinweise:
        (st.warning if stufe == "warnung" else st.info)(text)
    if not hinweise:
        st.success("Keine Auffälligkeiten.")
with rechts:
    st.subheader("Offene Fragen")
    for f in ss.fragen:
        st.markdown(f"- {f}")
    if not ss.fragen:
        st.markdown("Keine. Alle Räume und Anzahlen waren in den Notizen genannt.")

tab_pos, tab_angebot = st.tabs(["Positionen prüfen und korrigieren", "Angebot"])
with tab_pos:
    df = pd.DataFrame([{"Raum": RAEUME[p.raum], "Komponente": KOMP_NAME[p.komponente], "Anzahl": p.anzahl,
                        "Hinweis": p.hinweis} for p in aktuell])
    bearbeitet = st.data_editor(
        df, num_rows="dynamic", width="stretch", hide_index=True, key=f"editor_{len(ss.versionen)}",
        column_config={"Raum": st.column_config.SelectboxColumn(options=list(RAUM_KEY), required=True),
                       "Komponente": st.column_config.SelectboxColumn(options=list(KOMP_KEY), required=True),
                       "Anzahl": st.column_config.NumberColumn(min_value=1, max_value=50, step=1, required=True)})
    if st.button("Korrektur übernehmen"):
        neu = [Position(raum=RAUM_KEY[r.Raum], komponente=KOMP_KEY[r.Komponente], anzahl=int(r.Anzahl),
                        hinweis=r.Hinweis if isinstance(r.Hinweis, str) else "")
               for r in bearbeitet.dropna(subset=["Raum", "Komponente", "Anzahl"]).itertuples()]
        ss.versionen.append(("Von Hand korrigiert", neu))
        st.rerun()

with tab_angebot:
    a = angebot.erstellen(aktuell, stundensatz)
    tabelle = pd.DataFrame([{"Position": z["position"], "Räume": z["raeume"], "Menge": z["menge"],
                             "Material": angebot.euro(z["material_stk"]), "Montage": angebot.euro(z["montage_stk"]),
                             "Einzelpreis": angebot.euro(z["einzelpreis"]), "Gesamt": angebot.euro(z["gesamt"])}
                            for z in a["zeilen"]])
    st.dataframe(tabelle, width="stretch", hide_index=True)
    st.markdown(f"Netto **{angebot.euro(a['netto'])}**, MwSt. 19 % {angebot.euro(a['mwst'])}, "
                f"Brutto **{angebot.euro(a['brutto'])}**")
    if vorher is not None:
        diff = a["brutto"] - angebot.erstellen(vorher, stundensatz)["brutto"]
        st.markdown(f"Gegenüber der vorherigen Version: **{'+' if diff >= 0 else '−'}{angebot.euro(abs(diff))}** brutto")
    st.download_button("Angebot als CSV herunterladen", tabelle.to_csv(index=False, sep=";").encode("utf-8-sig"),
                       "angebot.csv", "text/csv")

st.markdown('<div class="schritt">3 Änderungswunsch des Kunden</div>', unsafe_allow_html=True)
wunsch = st.text_input("Was soll sich ändern?", placeholder=AENDERUNG_BEISPIEL)
if st.button("Änderung eintragen", disabled=not wunsch.strip()):
    try:
        neu = llm.aendern(aktuell, wunsch) if ki else aenderung.anwenden(aktuell, wunsch)
        if ki:
            ki_zaehlen()
    except Exception as e:
        st.warning(f"Sprachmodell nicht erreichbar ({type(e).__name__}). Die Änderung wurde mit Regeln eingetragen.")
        neu = aenderung.anwenden(aktuell, wunsch)
    if aenderung.unterschied(aktuell, neu):
        ss.versionen.append((wunsch, neu))
        st.rerun()
    st.warning("Daraus ließ sich keine Änderung ablesen. Bitte Raum und Komponente nennen, z. B. „Im Bad noch eine Steckdose“.")

if vorher is not None:
    st.subheader("Was sich geändert hat")
    st.dataframe(pd.DataFrame([{"Raum": d["raum"], "Komponente": KOMP_NAME[d["komponente"]], "Vorher": d["vorher"],
                                "Nachher": d["nachher"]} for d in aenderung.unterschied(vorher, aktuell)]),
                 width="stretch", hide_index=True)
    if st.button("Letzte Version verwerfen"):
        ss.versionen.pop()
        st.rerun()

with st.expander(f"Versionen ({len(ss.versionen)})"):
    for i, (titel, plan) in enumerate(ss.versionen, 1):
        st.markdown(f"{i}. {titel}: {sum(p.anzahl for p in plan)} Komponenten, "
                    f"{angebot.euro(angebot.erstellen(plan, stundensatz)['brutto'])} brutto")
