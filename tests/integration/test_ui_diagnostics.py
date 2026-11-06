from __future__ import annotations

from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_ui_displays_answer_evidence_diagnostics_and_empty_cache() -> None:
    harness = Path(__file__).parents[1] / "fixtures" / "ui_harness.py"
    app = AppTest.from_file(str(harness)).run()

    assert not app.exception
    assert app.title[0].value == "Bosch Rexroth Troubleshooting Assistant"
    assert "No supported answers are cached yet." in [item.value for item in app.caption]

    app.text_input[0].set_value("Explain the troubleshooting steps.")
    app.button[0].click()
    app.run()

    assert not app.exception
    text = " ".join(
        [item.value for item in app.markdown]
        + [item.value for item in app.caption]
    )
    assert "A source-supported answer." in text
    assert "alternative three" in text
    assert "guide.pdf" in text
    assert "Reranking" in text
    assert "Total" in text
    assert "Cache miss: no qualifying entry found." in text
    assert "0.420" in text
