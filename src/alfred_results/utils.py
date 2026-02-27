"""
utils
-----
General-purpose utilities for alfred-results.

Provides shared helpers that have no dependency on the CLI or Alfred-specific
types and can be imported independently of the rest of the package.

Alfred Script Filter items optionally carry a `uid` field — a stable,
unique identifier that Alfred uses to learn from the user's selection
history and reorder results across invocations.  :func:`path_to_uuid`
derives a deterministic UUID v5 from a resolved filesystem path so that
the same path always produces the same `uid`, enabling Alfred's learning
without any external state storage.
"""

from __future__ import annotations

from uuid import UUID, uuid5

# Custom UUID v5 namespace for alfred-results filesystem path identifiers.
# Derived via uuid5(NAMESPACE_DNS, "alfred-results") so it is stable,
# unique to this package, and follows the standard convention for custom
# namespaces (RFC 4122 Appendix C).
_PATH_UUID_NAMESPACE: UUID = UUID("a1f85bcb-d254-5636-8288-a612c8758c8b")


def path_to_uuid(path: str) -> str:
    """Derive a stable UUID v5 from a canonical filesystem path string.

    Uses :data:`_PATH_UUID_NAMESPACE` as the namespace so that the same
    absolute path always produces the same UUID.  Intended to provide Alfred
    with a stable `uid` that persists across workflow invocations, allowing
    Alfred to learn and reorder results based on usage history.

    Args:
        path: A canonical (expanded, resolved) absolute path string.  Callers
            should pass `str(Path(p).expanduser().resolve())` to ensure
            consistent results regardless of how the path was originally
            specified.

    Returns:
        A UUID v5 string in the standard `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
        format.

    Example::

        path_to_uuid("/Users/me/Downloads")
        # "d6e3c5a1-..."
    """
    return str(uuid5(_PATH_UUID_NAMESPACE, path))
