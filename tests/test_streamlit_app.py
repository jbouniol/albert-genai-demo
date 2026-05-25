from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_streamlit_demo_initial_render_controls() -> None:
    app = AppTest.from_file("app/streamlit_demo.py")
    app.run(timeout=15)

    assert len(app.exception) == 0
    assert app.segmented_control[0].value == "lucas"
    assert app.segmented_control[0].options == [
        "Lucas / grooming",
        "Emma / normal",
        "Mia / harassment",
    ]
    assert app.toggle[0].label == "Cached replay"
    assert app.button[0].label == "Run analysis"


def test_streamlit_demo_profile_switch_rerenders_case_file() -> None:
    app = AppTest.from_file("app/streamlit_demo.py")
    app.run(timeout=15)
    app.segmented_control[0].set_value("emma").run(timeout=15)

    assert len(app.exception) == 0
    page_markdown = "\n".join(markdown.value for markdown in app.markdown)
    assert "Emma" in page_markdown
    assert "Normal teen baseline" in page_markdown
