import os

from streamlit.testing.v1 import AppTest

os.environ.pop("OPENAI_API_KEY", None)


def starten():
    at = AppTest.from_file("../streamlit_app.py", default_timeout=30)
    at.run()
    return at


def knopf(at, label):
    return next(b for b in at.button if b.label == label)


def version(at) -> str:
    return next(m.value for m in at.markdown if "Version " in m.value and "hilfe" in m.value)


def test_beispiel_plan_aenderung_und_rueckgaengig():
    at = starten()
    assert not at.exception
    knopf(at, "Plan erstellen").click().run()
    assert not at.exception and "Version 1" in version(at)
    at.text_input(key="wunsch").input("Im Wohnzimmer statt der Antennendose lieber eine zweite Netzwerkdose.").run()
    knopf(at, "Änderung eintragen").click().run()
    assert not at.exception and "Version 2" in version(at)
    knopf(at, "Letzte Version verwerfen").click().run()
    assert "Version 1" in version(at)


def test_beide_beispiele_laufen():
    for name in ["Erdgeschoss", "Obergeschoss"]:
        at = starten()
        knopf(at, name).click().run()
        knopf(at, "Plan erstellen").click().run()
        assert not at.exception


def test_vorschlag_aus_pruefung_und_plus_minus():
    at = starten()
    knopf(at, "Plan erstellen").click().run()
    knopf(at, "Rauchmelder ergänzen").click().run()  # Flur hat im Beispiel keinen Rauchmelder
    assert not at.exception and "Rauchmelder ergänzen (Flur)" in version(at)
    at.button(key="p_kueche_steckdose").click().run()
    at.button(key="p_kueche_steckdose").click().run()
    assert "Version 3: Von Hand bearbeitet" in version(at)  # zwei Klicks, eine Version
    assert any(m.value == '<div class="anzahl">8</div>' for m in at.markdown)


def test_raum_anlegen():
    at = starten()
    knopf(at, "Plan erstellen").click().run()
    at.selectbox(key="neuer_raum").select("garage").run()
    at.selectbox(key="neuer_raum_komp").select("steckdose").run()
    knopf(at, "Raum anlegen").click().run()
    assert not at.exception
    assert any("Garage" in t.label for t in at.tabs)


def test_anleitung_und_projektseite():
    at = starten()
    knopf(at, "So funktioniert die App").click().run()
    assert not at.exception
    assert any("Wer macht was?" in m.value for m in at.markdown)
