"""Quick standalone check: does live Wikipedia collection work on this machine?

Run it to see whether the app can reach Wikipedia/Wikiquote and what it pulls.
If it fails, the full error/traceback is printed so we can diagnose (no internet,
proxy, SSL, etc.).

    python check_wikipedia.py "Albert Einstein"
"""

from __future__ import annotations

import sys
import traceback

from app.services.source_discovery import WikipediaSourceAdapter


def main() -> None:
    name = " ".join(sys.argv[1:]) or "Albert Einstein"
    print(f"Trying live collection for: {name!r}\n")
    try:
        result = WikipediaSourceAdapter()._discover(name)
        print("LIVE FETCH: OK")
        print("  resolved name :", result.persona.get("name"))
        print("  portrait URL  :", result.persona.get("portrait_url") or "(none)")
        print("  sources       :", len(result.sources))
        print("  is_demo       :", result.is_demo)
        if result.sources:
            sample = " ".join(result.sources[0].text.split())[:240]
            print("\n  sample text   :", sample, "…")
        print("\nGreat — live data works. Search this name in the app to build a real persona.")
    except Exception:  # noqa: BLE001
        print("LIVE FETCH FAILED — the app falls back to demo/placeholder data.\n")
        print("Reason (full traceback):\n")
        traceback.print_exc()
        print(
            "\nCommon causes: no internet, a corporate/ISP proxy, or SSL inspection. "
            "Paste this traceback back and I'll help fix it."
        )


if __name__ == "__main__":
    main()
