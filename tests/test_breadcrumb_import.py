"""Import checks for the breadcrumb widget."""

from __future__ import annotations


def test_breadcrumb_imports() -> None:
    from app.ui.widgets.breadcrumb import Breadcrumb, format_breadcrumb

    assert Breadcrumb is not None
    assert format_breadcrumb is not None


def test_format_breadcrumb() -> None:
    from app.ui.widgets.breadcrumb import format_breadcrumb

    assert format_breadcrumb(["Or\u00e7amento 260001_01", "Items"]) == "Or\u00e7amento 260001_01 > Items"
    assert (
        format_breadcrumb(["Or\u00e7amento 260001_01", "", "M\u00f3dulo: mod_1fix"])
        == "Or\u00e7amento 260001_01 > M\u00f3dulo: mod_1fix"
    )
