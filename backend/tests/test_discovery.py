"""Source-discovery adapter selection tests (offline, no network)."""

from __future__ import annotations

from app.services import source_discovery as sd


def test_default_adapter_is_wikipedia():
    # With source_mode=auto (default) and no search provider configured, the
    # live Wikipedia adapter is selected.
    adapter = sd.get_adapter()
    assert isinstance(adapter, sd.WikipediaSourceAdapter)


def test_force_demo_uses_bundled_corpus():
    result = sd.discover("Osho", force_demo=True)
    assert result.is_demo is True
    assert len(result.sources) >= 4


def test_section_splitter_blocks():
    adapter = sd.WikipediaSourceAdapter()
    text = ("Para one is reasonably long and informative.\n\n" * 30)
    blocks = adapter._split_sections(text)
    assert 1 <= len(blocks) <= 10
    assert all(b.strip() for b in blocks)
