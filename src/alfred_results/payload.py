"""
payload
-------
Alfred Script Filter top-level JSON payload.

Defines :class:`ScriptFilterCache` (the optional `"cache"` sub-object) and
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

    from alfred_results.result_item import Icon, ResultItem

_CACHE_SECONDS_MIN: int = 5
_CACHE_SECONDS_MAX: int = 86400

_RERUN_MIN: float = 0.1
_RERUN_MAX: float = 5.0


@dataclass(slots=True)
class ScriptFilterCache:
    """Alfred Script Filter `cache` sub-object.

    Controls how Alfred caches Script Filter results between invocations.
    When attached to a :class:`ScriptFilterPayload`, Alfred will reuse the
    previous result set for `seconds` seconds before re-running the script.

    Attributes:
        seconds: How long Alfred should cache results, in seconds.  Must be
            between `5` and `86400` (24 hours) inclusive.
        loosereload: When `True`, Alfred will attempt to show cached results
            immediately while re-running the script in the background.  When
            `False` (or omitted), Alfred waits for a fresh result before
            displaying anything.

    Raises:
        ValueError: If `seconds` is outside the range 5–86400.

    Example::

        cache = ScriptFilterCache(seconds=60, loosereload=True)
        cache.to_dict()
        # {"seconds": 60, "loosereload": True}
    """

    seconds: int
    loosereload: bool | None = None

    def __post_init__(self) -> None:
        """Validate field constraints after dataclass initialization.

        Raises:
            ValueError: If `seconds` is not between 5 and 86400 inclusive.
        """
        if not (_CACHE_SECONDS_MIN <= self.seconds <= _CACHE_SECONDS_MAX):
            raise ValueError(
                f"ScriptFilterCache.seconds must be between {_CACHE_SECONDS_MIN} and"
                f" {_CACHE_SECONDS_MAX}, got {self.seconds!r}."
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialize to Alfred's `cache` object shape.

        Returns:
            A JSON-serializable dict with `"seconds"` always present and
            `"loosereload"` included only when explicitly set.

        Example::

            ScriptFilterCache(seconds=3600).to_dict()
            # {"seconds": 3600}

            ScriptFilterCache(seconds=60, loosereload=True).to_dict()
            # {"seconds": 60, "loosereload": True}
        """
        data: dict[str, Any] = {"seconds": self.seconds}
        if self.loosereload is not None:
            data["loosereload"] = self.loosereload
        return data


@dataclass(slots=True)
class ScriptFilterPayload:
    """The complete Alfred Script Filter top-level JSON payload.

    Wraps the full response sent from a Script Filter to Alfred.  Use
    :meth:`to_json` to produce the final JSON string for Alfred, or
    :meth:`to_dict` to obtain a plain Python dict.  Use :meth:`info` to build
    a single-item informational payload without constructing a
    :class:`~alfred_results.result_item.ResultItem` directly.

    Attributes:
        cache: Optional caching configuration; see :class:`ScriptFilterCache`.
        rerun: If set, Alfred will automatically re-run the script after this
            many seconds.  Must be between `0.1` and `5.0` inclusive.
        skipknowledge: When `True`, Alfred will not apply its learned
            ordering to the result list for this invocation.
        variables: Top-level Alfred session variables available to all
            downstream workflow objects when any item from this payload is
            actioned.
        items: The list of :class:`~alfred_results.result_item.ResultItem`
            objects to display in Alfred's result list.

    Raises:
        ValueError: If `rerun` is set but outside the range 0.1–5.0.

    Example::

        payload = ScriptFilterPayload(
            rerun=1.0,
            variables={"mode": "search"},
            items=[ResultItem(title="foo", arg="bar")],
        )
        print(payload.to_json())
    """

    cache: ScriptFilterCache | None = None
    rerun: float | None = None
    skipknowledge: bool | None = None
    variables: Mapping[str, str] | None = None
    items: list[ResultItem] | None = None

    def __post_init__(self) -> None:
        """Validate field constraints after dataclass initialization.

        Raises:
            ValueError: If `rerun` is set but not between 0.1 and 5.0.
        """
        if self.rerun is not None and not (_RERUN_MIN <= self.rerun <= _RERUN_MAX):
            raise ValueError(
                f"ScriptFilterPayload.rerun must be between {_RERUN_MIN} and"
                f" {_RERUN_MAX}, got {self.rerun!r}."
            )

    @classmethod
    def info(
        cls,
        title: str,
        subtitle: str = "",
        *,
        icon: Icon | None = None,
    ) -> ScriptFilterPayload:
        """Build a single-item informational payload.

        Convenience factory that wraps `title` and an optional `subtitle`
        in a non-actionable :class:`~alfred_results.result_item.ResultItem`
        (`valid=False`) and returns a :class:`ScriptFilterPayload` containing
        only that item.  Intended for surfaces where the script needs to
        communicate a status or message to the user through Alfred's result
        list, such as "No results found" or "Connection failed".

        Args:
            title: The primary message shown in the Alfred result row.
            subtitle: Optional secondary text shown below the title.  An empty
                string (the default) is treated as unset and omitted from the
                serialized JSON.
            icon: Optional icon to display next to the row.  When `None`
                (the default) no icon key is emitted.

        Returns:
            A :class:`ScriptFilterPayload` containing a single non-actionable
            :class:`~alfred_results.result_item.ResultItem`.

        Example::

            # Minimal informational message
            payload = ScriptFilterPayload.info("No results found")
            print(payload.to_json())

            # With subtitle and custom icon
            payload = ScriptFilterPayload.info(
                "Connection failed",
                "Check your network and try again",
                icon=Icon(path="./icons/error.png"),
            )
        """
        from .result_item import ResultItem

        item = ResultItem(
            title=title,
            subtitle=subtitle if subtitle else None,
            valid=False,
            icon=icon,
        )
        return cls(items=[item])

    def to_dict(self) -> dict[str, Any]:
        """Serialize to Alfred's Script Filter top-level JSON shape as a dict.

        Builds the top-level dict that Alfred's Script Filter expects.  Only
        fields that have been explicitly set (i.e. are not `None`) are
        included.  To produce the final JSON string for Alfred, use
        :meth:`to_json` instead.

        Returns:
            A JSON-serializable dict conforming to the Alfred Script Filter
            top-level payload schema.

        The `variables` key is always present and includes `"script"` (the
        installed package name, or `"alfred-results"` when the package is
        vendored and not installed).  `"version"` is intentionally omitted
        because :func:`importlib.metadata.version` raises
        :exc:`~importlib.metadata.PackageNotFoundError` when the package is
        vendored inside an Alfred workflow bundle rather than installed via pip.

        Example::

            payload = ScriptFilterPayload(items=[ResultItem(title="foo")])
            payload.to_dict()
            # {"variables": {"script": "alfred-results"}, "items": [{"title": "foo"}]}
        """
        from importlib.metadata import PackageNotFoundError, metadata

        try:
            package_name = metadata(str(__package__))["Name"]
        except PackageNotFoundError:
            package_name = "alfred-results"

        # Default session variables are always emitted; user-supplied values win.
        default_session_variables: dict[str, str] = {
            "script": package_name,
        }

        data: dict[str, Any] = {}

        if self.cache is not None:
            data["cache"] = self.cache.to_dict()
        if self.rerun is not None:
            data["rerun"] = self.rerun
        if self.skipknowledge is not None:
            data["skipknowledge"] = self.skipknowledge
        if self.variables is not None:
            data["variables"] = default_session_variables | dict(self.variables)
        else:
            data["variables"] = default_session_variables
        if self.items is not None:
            data["items"] = [item.to_dict() for item in self.items]

        return data

    def to_json(self, **kwargs: Any) -> str:
        """Serialize to the Alfred Script Filter JSON string.

        Convenience method that calls :meth:`to_dict` and passes the result
        to :func:`json.dumps`.  Any keyword arguments are forwarded directly
        to :func:`json.dumps`, allowing control over formatting.

        Args:
            **kwargs: Keyword arguments forwarded to :func:`json.dumps`
                (e.g. `indent=2`, `sort_keys=True`,
                `separators=(",", ":")`)

        Returns:
            A JSON string conforming to the Alfred Script Filter top-level
            payload schema.

        Example::

            payload = ScriptFilterPayload(items=[ResultItem(title="foo")])

            # Compact output for Alfred
            print(payload.to_json())

            # Pretty-printed for debugging
            print(payload.to_json(indent=2))
        """
        from json import dumps

        return dumps(self.to_dict(), **kwargs)
