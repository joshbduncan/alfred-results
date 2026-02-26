"""
Shared pytest fixtures for alfred-results tests.
"""

from __future__ import annotations

import pytest

from alfred_results.result_item import Icon, IconResourceType, ItemType, Mod, ResultItem


@pytest.fixture
def simple_item() -> ResultItem:
    """A minimal ResultItem with only the required title field."""
    return ResultItem(title="My Result")


@pytest.fixture
def full_item() -> ResultItem:
    """A fully-populated ResultItem covering every optional field."""
    return ResultItem(
        title="report.pdf",
        subtitle="/Users/me/report.pdf",
        uid="abc-123",
        arg="/Users/me/report.pdf",
        valid=True,
        autocomplete="report",
        match="report pdf",
        type=ItemType.FILE,
        icon=Icon(path="/Users/me/report.pdf", resource_type=IconResourceType.FILEICON),
        mods=[
            Mod(
                key="cmd",
                valid=True,
                arg="/Users/me/report.pdf",
                subtitle="Open in Preview",
            ),
            Mod(key="alt", valid=False, subtitle="Not available"),
        ],
        text={"copy": "/Users/me/report.pdf", "largetype": "report.pdf"},
        quicklookurl="/Users/me/report.pdf",
        variables={"category": "reports"},
    )


@pytest.fixture
def fileicon() -> Icon:
    """An Icon using FILEICON resource type."""
    return Icon(path="/Users/me/Downloads", resource_type=IconResourceType.FILEICON)


@pytest.fixture
def filetype_icon() -> Icon:
    """An Icon using FILETYPE resource type (UTI)."""
    return Icon(path="com.adobe.pdf", resource_type=IconResourceType.FILETYPE)


@pytest.fixture
def custom_icon() -> Icon:
    """An Icon pointing to a bundled image with no resource_type."""
    return Icon(path="./icons/star.png")
