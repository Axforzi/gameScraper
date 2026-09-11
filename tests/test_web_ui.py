"""Offline HTML contract tests for the redesigned UI (REQ-UI-1..10, D8).

The app client renders the templates without any network, pinning the DOM
contract the server pages must keep so ``app.js`` wires up correctly and
the design system stays self-contained: CSRF meta + hidden input, exact
field names, a single ``<h1>`` per page, ``<noscript>`` fallbacks, zero
external CDN references, zero inline-script leftovers, and only
``tokens.css`` + ``app.css`` linked (REQ-UI-8).
"""

import re

CDN_URL_RE = re.compile(
    r"jsdelivr|bootstrapcdn|googleapis|cdnjs|fontawesome|material-icons"
)
CSS_LINK_RE = re.compile(r'<link rel="stylesheet" href="([^"]+\.css)"')
CSRF_META_RE = re.compile(r'name="csrf-token"')
CSRF_HIDDEN_RE = re.compile(r'name="csrf_token"')
GAME_LINK_RE = re.compile(r'name="game-link"')

# Only the local design-system stylesheets may be linked (REQ-UI-8).
EXPECTED_CSS = {"css/tokens.css", "css/app.css"}


def _page(client, path: str) -> str:
    response = client.get(path)
    assert response.status_code == 200
    return response.get_data(as_text=True)


def _assert_shared_contract(html: str, label: str) -> None:
    assert CSRF_META_RE.search(html), f"{label}: missing csrf meta"
    assert '<html lang="es"' in html, f"{label}: missing lang=es"
    assert "<noscript>" in html, f"{label}: missing noscript"
    assert not CDN_URL_RE.search(html), f"{label}: external CDN reference"
    assert "console.log" not in html, f"{label}: console.log leftover"
    assert "align=" not in html, f"{label}: deprecated align attribute"
    linked = CSS_LINK_RE.findall(html)
    assert {href.removeprefix("/static/") for href in linked} == EXPECTED_CSS, (
        f"{label}: unexpected stylesheets linked: {linked}"
    )
    assert "js/app.js" in html, f"{label}: app.js not wired"


def test_home_renders_search_contract(client) -> None:
    html = _page(client, "/")

    _assert_shared_contract(html, "home")

    # JS-off fallback form surfaces (REQ-UI-3/9): names byte-identical so
    # POST /juego keeps working without JavaScript.
    assert CSRF_HIDDEN_RE.search(html), "home: missing hidden csrf_token input"
    assert GAME_LINK_RE.search(html), "home: missing game-link field"
    assert '<form id="game-form" class="search-form" action="/juego" method="post">' in html
    assert 'id="game"' in html, "home: missing search input"
    assert 'id="search-submit"' in html, "home: missing submit button"

    # Panel + template the client script drives (D6/D7).
    assert 'id="results-panel"' in html, "home: missing results panel"
    assert 'id="panel-close"' in html, "home: missing panel close button"
    assert 'id="panel-backdrop"' in html, "home: missing panel backdrop"
    assert 'id="game-panel-template"' in html, "home: missing game panel template"
    assert html.count("<h1") == 1, "home: expected exactly one h1"


def test_ofertas_renders_store_sections_contract(client) -> None:
    html = _page(client, "/ofertas")

    _assert_shared_contract(html, "ofertas")

    # Exactly one h1 in main; one h2 per store section (REQ-UI-3).
    assert html.count("<h1") == 1, "ofertas: expected exactly one h1"
    assert html.count("<h2") == 3, "ofertas: expected one h2 per store section"

    sections = re.findall(r'data-store="([a-z]+)"', html)
    assert sections == ["steam", "egs", "gog"], f"ofertas: unexpected stores {sections}"

    assert 'id="offer-card-template"' in html, "ofertas: missing offer card template"
    assert 'id="toast"' in html, "ofertas: missing toast container"


def test_ofertas_keeps_view_more_links(client) -> None:
    """The per-store external links are unchanged (REQ-UI-3/4)."""
    html = _page(client, "/ofertas")

    for url in (
        "https://store.steampowered.com/search/?category1=998",
        "https://store.epicgames.com/es-ES/browse",
        "https://www.gog.com/en/games?discounted=true",
    ):
        assert url in html, f"ofertas: missing view-more URL {url}"


def test_covers_never_start_empty(client) -> None:
    """Cover images fall back to the local placeholder, never src=\"\"."""
    for path in ("/", "/ofertas"):
        html = _page(client, path)
        assert 'src=""' not in html, f"{path}: empty cover src"
        assert "data-placeholder=" in html, f"{path}: missing data-placeholder"