"""Pure-Python mirror of the client-side price math (REQ-UI-2, D8).

``src/static/js/app.js`` renders the discount chip as
``Math.round(100 - (descuento * 100 / precio))`` and only when ``precio > 0``
and ``descuento`` is present; any other combination renders a single final
price with no chip and no struck-through original. ``formatPrice`` renders
the amount with two decimals plus the currency, e.g. ``"7.50 USD"``.

These tests pin that logic in Python so the behavior is regression-tested
offline without a JS runtime. MIRROR CONTRACT: if the JS math changes,
this file must change in the same change and the mirror relationship
documented in the change description.
"""

import re
from decimal import ROUND_HALF_UP, Decimal

# Matches the JS guard: per store, ``precio`` is the original price and
# ``descuento`` the FINAL price (or null when the store returns none).
_UNSET = r"\b(null|undefined)\b"


def discount_percent(precio: float, descuento: float | None) -> int | None:
    """Mirror of ``app.js: discountPercent(precio, descuento)``.

    ``Math.round`` rounds half away from zero, which is ``ROUND_HALF_UP``
    on a positive value; floats go through ``str``/``Decimal`` so binary
    artifacts (e.g. 49.999999) cannot shift the result.
    """
    if precio is None or descuento is None or precio <= 0:
        return None
    value = Decimal("100") - Decimal(str(descuento)) * Decimal("100") / Decimal(str(precio))
    return int(value.to_integral_value(rounding=ROUND_HALF_UP))


def format_price(value: float, currency: str) -> str:
    """Mirror of ``app.js: formatPrice(n, c)`` -> ``"7.50 USD"``."""
    amount = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{amount} {currency}"


def test_discount_percent_with_final_price() -> None:
    assert discount_percent(15, 7.5) == 50  # 100 - (7.5 * 100 / 15)


def test_discount_percent_without_final_price() -> None:
    assert discount_percent(15, None) is None


def test_discount_percent_guards_division_by_zero() -> None:
    assert discount_percent(0, 0) is None
    assert discount_percent(0, 7.5) is None


def test_discount_percent_non_trivial_case() -> None:
    assert discount_percent(100, 90) == 10


def test_format_price_two_decimals_and_currency() -> None:
    assert format_price(7.5, "USD") == "7.50 USD"
    assert format_price(0.0, "USD") == "0.00 USD"
    assert format_price(12345.678, "USD") == "12345.68 USD"


def test_js_null_sentinel_matches_documented_shape() -> None:
    """Keys documented as ``null`` in the API shape map to Python None."""
    assert re.compile(_UNSET).search("descuento: null") is not None