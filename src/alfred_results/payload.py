"""
payload
-------
Alfred Script Filter top-level JSON payload.

Defines :class:`ScriptFilterCache` (the optional ``"cache"`` sub-object) and
:class:`ScriptFilterPayload` (the complete top-level Script Filter response).

Minimal Script Filter JSON example::

    {
        "cache": {
            "seconds": 3600
        },
        "rerun": 1,
        "skipknowledge": true,
        "variables": {
            "fruit": "banana",
            "vegetable": "carrot"
        },
        "items": [
            {
                "title": "My Result",
                "subtitle": "A description",
                "arg": "/path/to/file",
                "uid": "some-stable-uid"
            }
        ]
    }
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Mapping

    from alfred_results.result_item import ResultItem

_CACHE_SECONDS_MIN: int = 5
_CACHE_SECONDS_MAX: int = 86400

_RERUN_MIN: float = 0.1
_RERUN_MAX: float = 5.0


@dataclass(slots=True)
class ScriptFilterCache:
    """Alfred Script Filter ``cache`` sub-object.

    Controls how Alfred caches Script Filter results between invocations.
    When attached to a :class:`ScriptFilterPayload`, Alfred will reuse the
    previous result set for ``seconds`` seconds before re-running the script.

    Attributes:
        seconds: How long Alfred should cache results, in seconds.  Must be
            between ``5`` and ``86400`` (24 hours) inclusive.
        loosereload: When ``True``, Alfred will attempt to show cached results
            immediately while re-running the script in the background.  When
            ``False`` (or omitted), Alfred waits for a fresh result before
            displaying anything.

    Raises:
        ValueError: If ``seconds`` is outside the range 5–86400.

    Example::

        cache = ScriptFilterCache(seconds=60, loosereload=True)
        cache.to_alfred()
        # {"seconds": 60, "loosereload": True}
    """

    seconds: int
    loosereload: bool | None = None

    def __post_init__(self) -> None:
        """Validate field constraints after dataclass initialization.

        Raises:
            ValueError: If ``seconds`` is not between 5 and 86400 inclusive.
        """
        if not (_CACHE_SECONDS_MIN <= self.seconds <= _CACHE_SECONDS_MAX):
            raise ValueError(
                f"ScriptFilterCache.seconds must be between {_CACHE_SECONDS_MIN} and"
                f" {_CACHE_SECONDS_MAX}, got {self.seconds!r}."
            )

    def to_alfred(self) -> dict[str, Any]:
        """Serialize to Alfred's ``cache`` object shape.

        Returns:
            A JSON-serializable dict with ``"seconds"`` always present and
            ``"loosereload"`` included only when explicitly set.

        Example::

            ScriptFilterCache(seconds=3600).to_alfred()
            # {"seconds": 3600}

            ScriptFilterCache(seconds=60, loosereload=True).to_alfred()
            # {"seconds": 60, "loosereload": True}
        """
        data: dict[str, Any] = {"seconds": self.seconds}
        if self.loosereload is not None:
            data["loosereload"] = self.loosereload
        return data


@dataclass(slots=True)
class ScriptFilterPayload:
    """The complete Alfred Script Filter top-level JSON payload.

    Wraps the full response sent from a Script Filter to Alfred.  Serialize
    via :meth:`to_alfred` to obtain a JSON-ready dict, then pass it to
    :func:`json.dumps` for output.

    Attributes:
        cache: Optional caching configuration; see :class:`ScriptFilterCache`.
        rerun: If set, Alfred will automatically re-run the script after this
            many seconds.  Must be between ``0.1`` and ``5.0`` inclusive.
        skipknowledge: When ``True``, Alfred will not apply its learned
            ordering to the result list for this invocation.
        variables: Top-level Alfred session variables available to all
            downstream workflow objects when any item from this payload is
            actioned.
        items: The list of :class:`~alfred_results.result_item.ResultItem`
            objects to display in Alfred's result list.

    Raises:
        ValueError: If ``rerun`` is set but outside the range 0.1–5.0.

    Example::

        from json import dumps
        payload = ScriptFilterPayload(
            rerun=1.0,
            variables={"mode": "search"},
            items=[ResultItem(title="foo", arg="bar")],
        )
        dumps(payload.to_alfred())
    """

    cache: ScriptFilterCache | None = None
    rerun: float | None = None
    skipknowledge: bool | None = None
    variables: Mapping[str, str] | None = None
    items: list[ResultItem] | None = None

    def __post_init__(self) -> None:
        """Validate field constraints after dataclass initialization.

        Raises:
            ValueError: If ``rerun`` is set but not between 0.1 and 5.0.
        """
        if self.rerun is not None and not (_RERUN_MIN <= self.rerun <= _RERUN_MAX):
            raise ValueError(
                f"ScriptFilterPayload.rerun must be between {_RERUN_MIN} and"
                f" {_RERUN_MAX}, got {self.rerun!r}."
            )

    def to_alfred(self) -> dict[str, Any]:
        """Serialize to Alfred's Script Filter top-level JSON shape.

        Builds the top-level dict that Alfred's Script Filter expects.  Only
        fields that have been explicitly set (i.e. are not ``None``) are
        included.  Pass the result to :func:`json.dumps` to produce the final
        JSON string.

        Returns:
            A JSON-serializable dict conforming to the Alfred Script Filter
            top-level payload schema.

        Example::

            from json import dumps
            payload = ScriptFilterPayload(items=[ResultItem(title="foo")])
            dumps(payload.to_alfred())
            # '{"variables": {...}, "items": [{"title": "foo"}]}'
        """
        from importlib.metadata import PackageNotFoundError, metadata, version

        try:
            package_name = metadata(str(__package__))["Name"]
            package_version = version(package_name)
        except PackageNotFoundError:
            package_name = "alfred-results"
            package_version = ""

        # Default session variables are always emitted; user-supplied values win.
        default_session_variables: dict[str, str] = {
            "script": package_name,
            "version": package_version,
        }

        data: dict[str, Any] = {}

        if self.cache is not None:
            data["cache"] = self.cache.to_alfred()
        if self.rerun is not None:
            data["rerun"] = self.rerun
        if self.skipknowledge is not None:
            data["skipknowledge"] = self.skipknowledge
        if self.variables is not None:
            data["variables"] = default_session_variables | dict(self.variables)
        else:
            data["variables"] = default_session_variables
        if self.items is not None:
            data["items"] = [item.to_alfred() for item in self.items]

        return data
