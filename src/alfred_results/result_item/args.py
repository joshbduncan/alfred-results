"""
args
----
Type aliases for Alfred Script Filter argument values.

Alfred's JSON schema allows both a single string and an array of strings in
several places (`arg`, `action`, modifier `arg`).  `ArgValue` captures
that union so callers and type checkers get the correct type without repeating
the `str | Sequence[str]` expression throughout the codebase.
"""

from __future__ import annotations

from collections.abc import Sequence

# Alfred accepts a single string or an ordered list of strings as an argument
# value.  Using Sequence rather than list keeps the type covariant and allows
# callers to pass tuples, views, or other read-only sequences.
ArgValue = str | Sequence[str]
