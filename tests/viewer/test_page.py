"""The page ships with the package and has what its script uses (research R7)."""

import importlib.resources
import re

PAGE = (importlib.resources.files("apl.viewer") / "assets" / "index.html").read_text("utf-8")
IDS = [
    "level", "seed", "random", "dev-seeds", "generate", "arch", "run", "stop", "saved", "map",
    "slider", "follow", "fog", "solution", "panel", "stats", "message",
]  # fmt: skip


def test_page_has_every_element_the_script_uses() -> None:
    for name in IDS:
        assert f'id="{name}"' in PAGE, name


def test_page_never_inserts_model_text_as_html() -> None:
    # The only markup inserted is the server's own SVG drawing.
    assert re.findall(r"innerHTML\s*=\s*([^;]+);", PAGE) == ["data.svg"]
    assert "insertAdjacentHTML" not in PAGE and "outerHTML" not in PAGE


def test_page_loads_nothing_from_the_network() -> None:
    assert not re.search(r"""(src|href)=["']https?://""", PAGE)
