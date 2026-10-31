import os

from streamlit.testing.v1 import AppTest

os.environ.pop("OPENAI_API_KEY", None)


def starten():
    at = AppTest.from_file("../streamlit_app.py", default_timeout=30)
    at.run()
    return at


def test_beispiel_plan_aenderung_und_rueckgaengig():
    at = starten()
    assert not at.exception
    at.button[0].click().run()  # Plan erstellen
    assert not at.exception
    assert any("Version 1" in m.value for m in at.markdown)
    at.text_input[0].input("Im Wohnzimmer statt der Antennendose lieber eine zweite Netzwerkdose.").run()
    next(b for b in at.button if b.label == "Änderung eintragen").click().run()
    assert not at.exception
    assert any("Version 2" in m.value for m in at.markdown)
    next(b for b in at.button if b.label == "Letzte Version verwerfen").click().run()
    assert any("Version 1" in m.value for m in at.markdown)


def test_alle_beispiele_laufen():
    for name in ["Einfamilienhaus, Erdgeschoss", "Schlafbereich, Obergeschoss"]:
        at = starten()
        at.selectbox[0].select(name).run()
        at.button[0].click().run()
        assert not at.exception
