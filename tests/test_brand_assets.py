"""Guard the brand files under `docs/brand/` and their use in the README (spec 0024).

The assets are built outside the repository, so nothing regenerates them on a
change. These tests pin the properties a hand edit could break: an SVG that
needs an installed font, a file that loads something from a URL, a cover the
README no longer points at.
"""

from __future__ import annotations

import re
import struct
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_BRAND = _REPO_ROOT / "docs" / "brand"
_SVG_NAMESPACE = "http://www.w3.org/2000/svg"
_TITLED_SVGS = (
    "smartb100-mark.svg",
    "smartb100-mark-dark.svg",
    "smartb100-logo.svg",
    "smartb100-logo-dark.svg",
    "cover-light.svg",
    "cover-dark.svg",
)
_AFFILIATION = (
    "Independent project. Not affiliated with or endorsed by the Instituto Agronômico (IAC)."
)


def _brand_text_files() -> list[Path]:
    return sorted(p for p in _BRAND.rglob("*") if p.suffix in {".svg", ".css", ".json", ".md"})


def _readme() -> str:
    return (_REPO_ROOT / "README.md").read_text(encoding="utf-8")


def test_svgs_need_no_font() -> None:
    svgs = sorted(_BRAND.rglob("*.svg"))
    assert svgs, "no SVG under docs/brand/"
    with_text = [p.name for p in svgs if "<text" in p.read_text(encoding="utf-8")]
    assert with_text == []


def _foreign_urls(path: Path) -> list[str]:
    urls = re.findall(r"https?://[^\s\"')]+", path.read_text(encoding="utf-8"))
    return [u for u in urls if u != _SVG_NAMESPACE]


def test_svgs_load_nothing() -> None:
    files = _brand_text_files()
    assert files, "no text file under docs/brand/"
    loading = {p.relative_to(_BRAND).as_posix(): urls for p in files if (urls := _foreign_urls(p))}
    assert loading == {}


@pytest.mark.parametrize("name", _TITLED_SVGS)
def test_every_svg_has_a_title(name: str) -> None:
    assert re.search(r"<title>[^<]+</title>", (_BRAND / name).read_text(encoding="utf-8"))


def test_cover_follows_the_theme() -> None:
    readme = _readme()
    picture = re.search(r"<picture>.*?</picture>", readme, re.S)
    assert picture, "README has no <picture>"
    assert readme.lstrip().startswith("<picture>")
    block = picture.group(0)
    assert re.search(
        r'<source media="\(prefers-color-scheme: dark\)" srcset="docs/brand/cover-dark.svg"\s*/?>',
        block,
    )
    img = re.search(r"<img [^>]*>", block)
    assert img
    assert 'src="docs/brand/cover-light.svg"' in img.group(0)
    assert re.search(r'alt="[^"]*SmartB100[^"]*"', img.group(0))


def test_favicon_ico_holds_three_sizes() -> None:
    data = (_BRAND / "favicon" / "favicon.ico").read_bytes()
    reserved, kind, count = struct.unpack("<HHH", data[:6])
    assert (reserved, kind) == (0, 1)
    sizes = sorted(data[6 + 16 * i] or 256 for i in range(count))
    assert sizes == [16, 32, 48]


def test_readme_states_the_affiliation() -> None:
    readme = _readme()
    license_section = readme.split("## License", 1)[1]
    assert _AFFILIATION in license_section
