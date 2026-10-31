"""Wunschplan: aus Notizen eines Kundengesprächs werden Positionen, ein Installationsplan und ein Angebot."""
import datetime as dt
import hashlib
import os
from html import escape

import pandas as pd
import streamlit as st

from wp import aenderung, angebot, grundriss, llm, pruefung, regeln
from wp.katalog import KOMPONENTEN, RAEUME, STUNDENSATZ

try:  # Schlüssel aus den Streamlit-Secrets, falls gesetzt
    os.environ.setdefault("OPENAI_API_KEY", st.secrets["OPENAI_API_KEY"])
except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    pass

MAX_KI_AUFRUFE = 20
SPRACHMODELL, REGELN = "Sprachmodell (gpt-4o-mini)", "Regeln (offline)"

BEISPIELE = {
    "Erdgeschoss": (
        "Wohnzimmer: zwei Doppelsteckdosen am Sofa, an der TV-Wand eine Dreifachsteckdose, eine Netzwerkdose und eine "
        "Antennendose. Deckenlicht dimmbar.\n"
        "Küche mit Herdanschluss, sechs Steckdosen über der Arbeitsplatte und zwei Einbaustrahler-Auslässe an der Decke, "
        "dazu ein Lichtschalter an der Tür.\n"
        "Flur: Licht über Taster an beiden Enden und eine Steckdose für den Staubsauger.\n"
        "Gäste-WC nur eine Deckenleuchte mit Schalter.\n"
        "Auf der Terrasse eine Außensteckdose und eine Wandleuchte mit Bewegungsmelder."),
    "Obergeschoss": (
        "Im Schlafzimmer links und rechts vom Bett je eine Doppelsteckdose, dazu eine Deckenleuchte, die man an der Tür "
        "und am Bett schalten kann.\n"
        "Kinderzimmer bekommt einen Rauchmelder, zwei Doppelsteckdosen und eine Netzwerkdose am Schreibtisch.\n"
        "Bad mit Spiegelleuchte über dem Waschbecken, Deckenlicht mit Schalter und einer Doppelsteckdose neben dem Spiegel."),
}
WUNSCH_VORSCHLAEGE = {  # Beschriftung des Knopfs: Text, der ins Feld übernommen wird
    "Antennendose raus, zweite Netzwerkdose": "Im Wohnzimmer statt der Antennendose lieber eine zweite Netzwerkdose.",
    "Küche: sechs statt vier Steckdosen": "In der Küche sechs statt vier Steckdosen.",
    "Bad: noch eine Steckdose": "Im Bad noch eine Steckdose neben dem Spiegel."}
HAND = "Von Hand bearbeitet"

st.set_page_config(page_title="Wunschplan", page_icon="🔌", layout="wide")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&display=swap');
:root { --grund:#F1F0EE; --flaeche:#FFFFFF; --tinte:#17171C; --rot:#FD2950; --linie:#D6D4D0; --grau:#5D6C7B; --neu:#12A150; }
html, body, .stApp, .stApp p, .stApp li, .stApp label, .stApp input, .stApp textarea, .stApp button, .stApp h1, .stApp h2, .stApp h3 {
  font-family: 'IBM Plex Sans', Arial, sans-serif !important; }
header[data-testid="stHeader"] { display: none; }
.block-container { padding-top: 1rem !important; max-width: 1180px; }
.appbar { background: var(--rot); color: #fff; border-radius: 12px; padding: .7rem 1rem; display: flex; align-items: center;
  justify-content: space-between; gap: 1rem; flex-wrap: wrap; }
.marke { display: flex; align-items: center; gap: .55rem; font-weight: 700; font-size: 1.25rem; letter-spacing: .01em; }
.schritte { display: flex; gap: .35rem; flex-wrap: wrap; }
.schritte a { color: #fff; text-decoration: none; display: flex; align-items: center; gap: .4rem; padding: .3rem .65rem;
  border-radius: 999px; font-size: .92rem; }
.schritte a:hover, .schritte a:focus-visible { background: rgba(255,255,255,.18); outline: none; }
.schritte .nr { width: 1.45rem; height: 1.45rem; border-radius: 50%; border: 1.5px solid #fff; display: grid; place-items: center;
  font-size: .8rem; font-weight: 600; }
.schritte a.fertig .nr { background: #fff; color: var(--rot); }
.schritte a.jetzt { background: #fff; color: var(--tinte); font-weight: 600; }
.schritte a.jetzt .nr { border-color: var(--tinte); }
.portfolio-banner { background: var(--tinte); color: #F1F0EE; padding: .5rem .9rem; font-size: .9rem; border-radius: 0 0 10px 10px;
  margin: 0 .6rem 1.6rem; }
.portfolio-banner a { color: #FFB3C1; }
.titel { font-size: clamp(2rem, 4.2vw, 3.1rem); font-weight: 700; line-height: 1.05; margin: .2rem 0 .6rem; max-width: 20ch; }
.lead { font-size: 1.12rem; color: #3A3F46; max-width: 58ch; margin-bottom: 1.2rem; }
.schraffur { height: 16px; margin: 2rem 0 1.4rem; border-top: 1.5px solid var(--tinte); border-bottom: 1.5px solid var(--tinte);
  background: repeating-linear-gradient(45deg, var(--tinte) 0 1.4px, transparent 1.4px 7px); opacity: .55; }
.abschnitt { display: flex; align-items: baseline; gap: .7rem; margin-bottom: .4rem; scroll-margin-top: 1rem; }
.abschnitt .nr { color: var(--rot); font-weight: 700; font-size: 1.5rem; }
.abschnitt h2 { font-size: 1.6rem !important; font-weight: 700 !important; margin: 0 !important; padding: 0 !important; }
.hilfe { color: var(--grau); margin-bottom: .8rem; max-width: 70ch; }
.planflaeche { background: var(--flaeche); border: 1px solid var(--linie); border-radius: 12px; padding: 14px; overflow-x: auto; }
.planflaeche svg { min-width: 720px; display: block; }
.legende { display: flex; flex-wrap: wrap; gap: .2rem 1rem; font-size: .85rem; color: #3A3F46; margin: .5rem 0 1rem; }
.leg { display: inline-flex; align-items: center; gap: .1rem; }
.pruef { border-left: 4px solid var(--grau); background: var(--flaeche); padding: .55rem .8rem; margin: .5rem 0 .25rem;
  border-radius: 0 8px 8px 0; font-size: .95rem; }
.pruef.warnung { border-left-color: var(--rot); }
.raumzeile { padding-top: .35rem; line-height: 1.25; }
.raumzeile small { color: var(--grau); }
.anzahl { text-align: center; font-weight: 600; font-size: 1.1rem; padding-top: .35rem; }
.papier { background: var(--flaeche); border: 1px solid var(--linie); border-top: 6px solid var(--rot); border-radius: 4px;
  padding: 1.4rem 1.6rem; box-shadow: 0 10px 30px rgba(23,23,28,.07); }
.papier h3 { font-size: 1.35rem !important; margin: 0 0 .2rem !important; }
.papier .meta { color: var(--grau); font-size: .9rem; margin-bottom: 1rem; }
.papier table { width: 100%; border-collapse: collapse; font-size: .92rem; font-variant-numeric: tabular-nums; }
.papier th { text-align: left; font-weight: 600; background: var(--grund); padding: .45rem .5rem; border-bottom: 1.5px solid var(--tinte); }
.papier td { padding: .45rem .5rem; border-bottom: 1px solid var(--linie); vertical-align: top; }
.papier td small { color: var(--grau); }
.papier .r { text-align: right; white-space: nowrap; }
.papier table, .papier th, .papier td { border-left: 0 !important; border-right: 0 !important; border-top: 0 !important; }
.papier table { margin: 0 !important; display: table !important; }
.papier .summen td { border: 0; padding: .2rem .5rem; }
.papier .gesamt td { font-weight: 700; font-size: 1.05rem; border-top: 1.5px solid var(--tinte); }
.diff { width: 100%; border-collapse: collapse; font-size: .95rem; background: var(--flaeche); border-radius: 10px; overflow: hidden; }
.diff td, .diff th { padding: .45rem .7rem; border-bottom: 1px solid var(--linie); text-align: left; }
.diff .plus { color: var(--neu); font-weight: 600; } .diff .minus { color: var(--rot); font-weight: 600; }
.version { display: flex; justify-content: space-between; gap: 1rem; padding: .45rem 0; border-bottom: 1px dashed var(--linie); }
.version b { color: var(--rot); margin-right: .4rem; }
.leer { background: var(--flaeche); border: 1.5px dashed var(--linie); border-radius: 12px; padding: 1.4rem; color: var(--grau); }
@media (max-width: 640px) { .schritte .lbl { display: none; } .titel { max-width: none; }
  .stTabs [data-testid="stHorizontalBlock"] { flex-wrap: nowrap !important; gap: .4rem !important; }
  .stTabs [data-testid="stColumn"] { min-width: 0 !important; width: auto !important; }
  .papier { padding: 1rem .8rem; } .papier .ep { display: none; } }
</style>""", unsafe_allow_html=True)

ss = st.session_state
ss.setdefault("versionen", [])  # Liste aus (Beschreibung, [Position])
ss.setdefault("fragen", [])
ss.setdefault("ki_aufrufe", 0)
ss.setdefault("notiz", BEISPIELE["Erdgeschoss"])
ss.setdefault("modus", SPRACHMODELL if llm.available() else REGELN)
ss.setdefault("audio_hash", None)
ss.setdefault("meldung", None)
ss.setdefault("wunsch", "")


def ki_frei() -> bool:
    return llm.available() and ss.ki_aufrufe < MAX_KI_AUFRUFE


def mit_ki() -> bool:
    return ss.modus == SPRACHMODELL and ki_frei()


def aktuell():
    return ss.versionen[-1][1]


def neue_version(titel, positionen):
    if titel == HAND and ss.versionen and ss.versionen[-1][0] == HAND:
        ss.versionen[-1] = (titel, positionen)  # mehrere Klicks von Hand ergeben eine Version
    else:
        ss.versionen.append((titel, positionen))


def beispiel_laden(name):
    ss.notiz = BEISPIELE[name]


def audio_uebernehmen():
    datei = ss.get("audio")
    if datei is None:
        return
    daten = datei.getvalue()
    h = hashlib.sha1(daten).hexdigest()
    if h == ss.audio_hash or not ki_frei():
        return
    ss.audio_hash = h
    try:
        text = llm.transkribieren(daten)
        ss.ki_aufrufe += 1
        ss.notiz = f"{ss.notiz.rstrip()}\n{text}".strip()
        ss.meldung = ("ok", "Diktat übernommen und unten an die Notizen angehängt.", "notizen")
    except Exception as e:
        ss.meldung = ("fehler", f"Diktat konnte nicht umgewandelt werden ({type(e).__name__}). Bitte tippe die Notizen ein.", "notizen")


def plan_erstellen():
    try:
        if mit_ki():
            plan = llm.extrahieren(ss.notiz)
            ss.ki_aufrufe += 1
        else:
            plan = regeln.extrahieren(ss.notiz)
        ss.meldung = None
    except Exception as e:  # Modell nicht erreichbar: mit Regeln weiterarbeiten
        plan = regeln.extrahieren(ss.notiz)
        ss.meldung = ("fehler", f"Sprachmodell nicht erreichbar ({type(e).__name__}). Der Plan wurde mit Regeln erstellt.", "notizen")
    ss.versionen = [("Erster Entwurf", plan.positionen)]
    ss.fragen = plan.offene_fragen


def anpassen(raum, komp, delta):
    neue_version(HAND, aenderung.anpassen(aktuell(), raum, komp, delta))


def vorschlag_uebernehmen(beschriftung, schritte):
    plan = aktuell()
    for raum, komp, delta in schritte:
        plan = aenderung.anpassen(plan, raum, komp, delta)
    neue_version(f"{beschriftung} ({RAEUME[schritte[0][0]]})", plan)


def hinzufuegen(raum_key, komp_key):
    raum, komp = ss[raum_key], ss[komp_key]
    if raum and komp:
        anpassen(raum, komp, 1)
        ss[komp_key] = None
        if raum_key == "neuer_raum":
            ss[raum_key] = None


def wunsch_setzen(text):
    ss.wunsch = text


def aenderung_eintragen():
    wunsch = ss.wunsch.strip()
    if not wunsch:
        return
    try:
        if mit_ki():
            neu = llm.aendern(aktuell(), wunsch)
            ss.ki_aufrufe += 1
        else:
            neu = aenderung.anwenden(aktuell(), wunsch)
    except Exception as e:
        neu = aenderung.anwenden(aktuell(), wunsch)
        ss.meldung = ("fehler", f"Sprachmodell nicht erreichbar ({type(e).__name__}). Die Änderung wurde mit Regeln eingetragen.", "aenderungen")
    if aenderung.unterschied(aktuell(), neu):
        ss.versionen.append((wunsch, neu))
        ss.wunsch = ""
        ss.meldung = ("ok", "Änderung als neue Version eingetragen. Im Plan oben ist sie markiert.", "aenderungen")
    else:
        ss.meldung = ("fehler", "Daraus ließ sich keine Änderung ablesen. Nenne Raum und Komponente, "
                                "z. B. „Im Bad noch eine Steckdose“.", "aenderungen")


def verwerfen():
    ss.versionen.pop()


def meldung_zeigen(ort):
    if ss.meldung and ss.meldung[2] == ort:
        art, text, _ = ss.meldung
        (st.success if art == "ok" else st.warning)(text)
        ss.meldung = None


# Kopfzeile: Marke und Schritte. Ein Schritt ist erledigt, sobald es dazu ein Ergebnis gibt.
hat_plan = bool(ss.versionen)
schritte = [("notizen", "Notizen", hat_plan), ("plan", "Plan prüfen", False),
            ("angebot", "Angebot", False), ("aenderungen", "Änderungen", len(ss.versionen) > 1)]
jetzt = "notizen" if not hat_plan else "plan"
links = "".join(f'<a href="#s-{k}" class="{"jetzt" if k == jetzt else "fertig" if fertig else ""}">'
                f'<span class="nr">{"✓" if fertig and k != jetzt else i}</span><span class="lbl">{t}</span></a>'
                for i, (k, t, fertig) in enumerate(schritte, 1))
st.markdown(f"""<div class="appbar"><div class="marke"><svg width="26" height="26" viewBox="0 0 26 26" aria-hidden="true">
<rect width="26" height="26" rx="6" fill="#fff"/><path d="M6 15 A7 7 0 0 1 20 15 Z" fill="none" stroke="#FD2950" stroke-width="2.2"/>
<line x1="13" y1="8" x2="13" y2="4.5" stroke="#FD2950" stroke-width="2.2" stroke-linecap="round"/>
<line x1="4" y1="19.5" x2="22" y2="19.5" stroke="#17171C" stroke-width="2.2" stroke-linecap="round"/></svg>Wunschplan</div>
<nav class="schritte" aria-label="Schritte">{links}</nav></div>
<div class="portfolio-banner">This app was developed by Amrina as part of a portfolio.
<a href="https://sayamrina.github.io/" target="_blank" rel="noopener">View the portfolio →</a></div>
<div class="titel">Vom Kundengespräch zum Angebot.</div>
<p class="lead">Notizen rein, Plan und Angebot raus. Will der Kunde später etwas anders haben, trägst du es als neue Version ein
und siehst sofort, was sich ändert und was es kostet.</p>""", unsafe_allow_html=True)

# 1 Notizen
st.markdown('<div class="abschnitt" id="s-notizen"><span class="nr">1</span><h2>Notizen</h2></div>'
            '<p class="hilfe">Schreib auf, was der Kunde in welchem Raum haben möchte, so wie du es im Gespräch notierst. '
            'Oder lade ein Beispiel.</p>', unsafe_allow_html=True)
links_sp, rechts_sp = st.columns([3, 2], gap="large")
with rechts_sp:
    st.markdown("**Beispiel laden**")
    b1, b2 = st.columns(2)
    for spalte, name in zip((b1, b2), BEISPIELE, strict=True):
        spalte.button(name, key=f"bsp_{name}", on_click=beispiel_laden, args=(name,), use_container_width=True)
    if ki_frei():
        st.audio_input("Notizen einsprechen", key="audio", on_change=audio_uebernehmen,
                       help="Wird auf Deutsch in Text umgewandelt und an die Notizen angehängt.")
    else:
        st.caption("Diktat und Sprachmodell brauchen einen API-Schlüssel. Ohne Schlüssel erkennt die App die Notizen mit Regeln.")
    with st.popover("Einstellungen", use_container_width=True):
        st.radio("Erkennung", [SPRACHMODELL, REGELN] if ki_frei() else [REGELN], key="modus",
                 help="Das Sprachmodell versteht auch Kürzel und Tippfehler. Die Regeln brauchen ordentliche Sätze.")
        st.caption(f"Bis zu {MAX_KI_AUFRUFE} Modellaufrufe pro Besuch, danach weiter mit Regeln.")
with links_sp:
    st.text_area("Was wünscht sich der Kunde?", key="notiz", height=230,
                 placeholder="z. B. Im Schlafzimmer links und rechts vom Bett je eine Doppelsteckdose …")
    st.button("Plan erstellen", type="primary", on_click=plan_erstellen, disabled=not ss.notiz.strip())
meldung_zeigen("notizen")

# 2 Plan prüfen
st.markdown('<div class="schraffur"></div><div class="abschnitt" id="s-plan"><span class="nr">2</span><h2>Plan prüfen</h2></div>',
            unsafe_allow_html=True)
if not ss.versionen:
    st.markdown('<div class="leer">Noch kein Plan. Lade oben ein Beispiel oder schreib eigene Notizen und klick auf '
                '„Plan erstellen“.</div>', unsafe_allow_html=True)
    st.stop()

plan_jetzt = aktuell()
vorher = ss.versionen[-2][1] if len(ss.versionen) > 1 else None
st.markdown(f'<p class="hilfe">Version {len(ss.versionen)}: {escape(ss.versionen[-1][0].rstrip("."))}. '
            'Die Lage im Raum ist schematisch.</p>'
            f'<div class="planflaeche">{grundriss.zeichnen(plan_jetzt, vorher)}</div>'
            f'<div class="legende">{grundriss.legende()}</div>', unsafe_allow_html=True)

bearbeiten_sp, pruef_sp = st.columns([3, 2], gap="large")
with pruef_sp:
    st.markdown("#### Prüfung")
    hinweise = pruefung.pruefen(plan_jetzt)
    for i, (stufe, text, vorschlag) in enumerate(hinweise):
        st.markdown(f'<div class="pruef {stufe}">{escape(text)}</div>', unsafe_allow_html=True)
        if vorschlag:
            st.button(vorschlag[0], key=f"fix_{i}_{len(ss.versionen)}", on_click=vorschlag_uebernehmen, args=vorschlag)
    if not hinweise:
        st.markdown('<div class="pruef">Keine Auffälligkeiten.</div>', unsafe_allow_html=True)
    if ss.fragen:
        st.markdown("#### Offene Fragen")
        for f in ss.fragen:
            st.markdown(f"- {f}")
with bearbeiten_sp:
    st.markdown("#### Räume bearbeiten")
    raeume = list(dict.fromkeys(p.raum for p in plan_jetzt))
    tabs = st.tabs([RAEUME[r] for r in raeume] + ["+ Raum"])
    for raum, tab in zip(raeume, tabs, strict=False):
        with tab:
            for p in [p for p in plan_jetzt if p.raum == raum]:
                c_name, c_minus, c_n, c_plus = st.columns([6, 1, 1, 1], vertical_alignment="center")
                hinweis = f"<br><small>{escape(p.hinweis)}</small>" if p.hinweis else ""
                c_name.markdown(f'<div class="raumzeile">{escape(KOMPONENTEN[p.komponente][0])}{hinweis}</div>',
                                unsafe_allow_html=True)
                c_minus.button("−", key=f"m_{raum}_{p.komponente}", on_click=anpassen, args=(raum, p.komponente, -1),
                               help="Eins weniger", use_container_width=True)
                c_n.markdown(f'<div class="anzahl">{p.anzahl}</div>', unsafe_allow_html=True)
                c_plus.button("+", key=f"p_{raum}_{p.komponente}", on_click=anpassen, args=(raum, p.komponente, 1),
                              help="Eins mehr", use_container_width=True)
            c_k, c_b = st.columns([4, 2], vertical_alignment="bottom")
            ss.setdefault(f"raum_{raum}", raum)
            c_k.selectbox("Komponente hinzufügen", list(KOMPONENTEN), key=f"neu_{raum}", index=None,
                          format_func=lambda k: KOMPONENTEN[k][0], placeholder="Komponente wählen")
            c_b.button("Hinzufügen", key=f"add_{raum}", on_click=hinzufuegen, args=(f"raum_{raum}", f"neu_{raum}"),
                       use_container_width=True)
    with tabs[-1]:
        c_r, c_k, c_b = st.columns([3, 3, 2], vertical_alignment="bottom")
        c_r.selectbox("Raum", [r for r in RAEUME if r not in raeume], key="neuer_raum", index=None,
                      format_func=RAEUME.get, placeholder="Raum wählen")
        c_k.selectbox("Erste Komponente", list(KOMPONENTEN), key="neuer_raum_komp", index=None,
                      format_func=lambda k: KOMPONENTEN[k][0], placeholder="Komponente wählen")
        c_b.button("Raum anlegen", on_click=hinzufuegen, args=("neuer_raum", "neuer_raum_komp"), use_container_width=True)

# 3 Angebot
st.markdown('<div class="schraffur"></div><div class="abschnitt" id="s-angebot"><span class="nr">3</span><h2>Angebot</h2></div>'
            '<p class="hilfe">Material und Montage je Position, gerechnet im Code. Katalog und Preise sind Beispielwerte.</p>',
            unsafe_allow_html=True)
c_kunde, c_satz = st.columns(2)
kunde = c_kunde.text_input("Kunde", "Familie Beispiel")
stundensatz = c_satz.number_input("Stundensatz Montage (€ netto)", 30.0, 150.0, STUNDENSATZ, 1.0)
a = angebot.erstellen(plan_jetzt, stundensatz)
heute = dt.date.today().strftime("%d.%m.%Y")
nummer = f"WP-{dt.date.today():%Y}-001-V{len(ss.versionen)}"
zeilen = "".join(f'<tr><td>{i}</td><td class="r">{z["menge"]}</td><td>{escape(z["position"])}<br><small>{escape(z["raeume"])}</small></td>'
                 f'<td class="r ep">{angebot.euro(z["einzelpreis"])}</td><td class="r">{angebot.euro(z["gesamt"])}</td></tr>'
                 for i, z in enumerate(a["zeilen"], 1))
differenz = ""
if vorher is not None:
    d = a["brutto"] - angebot.erstellen(vorher, stundensatz)["brutto"]
    differenz = f" Gegenüber Version {len(ss.versionen) - 1}: {'+' if d >= 0 else '−'}{angebot.euro(abs(d))} brutto."
st.markdown(f"""<div class="papier"><h3>Angebot {nummer}</h3>
<div class="meta">Kunde: {escape(kunde)} | Datum: {heute}{differenz}</div>
<table><thead><tr><th>Pos.</th><th class="r">Menge</th><th>Bezeichnung</th><th class="r ep">Einzelpreis</th><th class="r">Gesamt</th></tr></thead>
<tbody>{zeilen}</tbody></table>
<table class="summen"><tr><td></td><td class="r">Summe netto</td><td class="r" style="width:8rem">{angebot.euro(a["netto"])}</td></tr>
<tr><td></td><td class="r">MwSt. 19 %</td><td class="r">{angebot.euro(a["mwst"])}</td></tr>
<tr class="gesamt"><td></td><td class="r">Gesamt brutto</td><td class="r">{angebot.euro(a["brutto"])}</td></tr></table></div>""",
            unsafe_allow_html=True)
c_pdf, c_csv, _ = st.columns([2, 2, 3])
c_pdf.download_button("Angebot als PDF", angebot.pdf(plan_jetzt, stundensatz, kunde, nummer, heute), f"{nummer}.pdf",
                      "application/pdf", type="primary", use_container_width=True)
csv = pd.DataFrame([{"Position": z["position"], "Räume": z["raeume"], "Menge": z["menge"], "Einzelpreis": z["einzelpreis"],
                     "Gesamt": z["gesamt"]} for z in a["zeilen"]]).to_csv(index=False, sep=";").encode("utf-8-sig")
c_csv.download_button("Als CSV", csv, f"{nummer}.csv", "text/csv", use_container_width=True)

# 4 Änderungen
st.markdown('<div class="schraffur"></div><div class="abschnitt" id="s-aenderungen"><span class="nr">4</span><h2>Änderungen</h2></div>'
            '<p class="hilfe">Ruft der Kunde an und will etwas anders haben, schreib es so auf, wie er es sagt. '
            'Daraus wird eine neue Version mit Markierung im Plan.</p>', unsafe_allow_html=True)
st.text_input("Was soll sich ändern?", key="wunsch", placeholder="z. B. Im Bad noch eine Steckdose neben dem Spiegel.")
st.caption("Beispiele zum Ausprobieren:")
vorschlag_spalten = st.columns(len(WUNSCH_VORSCHLAEGE))
for spalte, (label, text) in zip(vorschlag_spalten, WUNSCH_VORSCHLAEGE.items(), strict=True):
    spalte.button(label, key=f"w_{label}", on_click=wunsch_setzen, args=(text,), use_container_width=True)
st.button("Änderung eintragen", type="primary", on_click=aenderung_eintragen, disabled=not ss.wunsch.strip())
meldung_zeigen("aenderungen")

if vorher is not None:
    reihen = ""
    for d in aenderung.unterschied(vorher, plan_jetzt):
        klasse = "plus" if d["nachher"] > d["vorher"] else "minus"
        reihen += (f'<tr><td>{escape(d["raum"])}</td><td>{escape(KOMPONENTEN[d["komponente"]][0])}</td>'
                   f'<td>{d["vorher"]}</td><td class="{klasse}">{d["nachher"]}</td></tr>')
    st.markdown("#### Was sich geändert hat")
    st.markdown(f'<table class="diff"><thead><tr><th>Raum</th><th>Komponente</th><th>Vorher</th><th>Nachher</th></tr></thead>'
                f'<tbody>{reihen}</tbody></table>', unsafe_allow_html=True)

st.markdown("#### Versionen")
zeilen_v = ""
for i, (titel, plan) in enumerate(ss.versionen, 1):
    zeilen_v += (f'<div class="version"><span><b>V{i}</b>{escape(titel)}</span>'
                 f'<span>{angebot.euro(angebot.erstellen(plan, stundensatz)["brutto"])}</span></div>')
st.markdown(zeilen_v, unsafe_allow_html=True)
if len(ss.versionen) > 1:
    st.button("Letzte Version verwerfen", on_click=verwerfen)
