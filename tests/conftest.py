"""Shared pytest configuration.

Windows-only stability guard: many tests spin up throwaway SQLAlchemy engines
(``sqlite:///:memory:``) and Qt widgets without disposing them, leaving native
objects for the cyclic garbage collector to finalize at an arbitrary later
moment. On Windows that finalization occasionally fires *in the middle of another
test's SQLite fetch* and aborts the whole run with a native "access violation".

Disabling the *cyclic* collector for the duration of the session stops it from
firing mid-test; reference-counted cleanup (the common case) still happens
immediately at each fixture teardown, so memory does not grow unbounded. This is
far cheaper than forcing a full ``gc.collect()`` after every test.
"""

from __future__ import annotations

import gc

import pytest


@pytest.fixture(autouse=True, scope="session")
def _disable_cyclic_gc_during_session():
    """Keep the cyclic GC from running mid-test on Windows."""
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if was_enabled:
            gc.enable()
