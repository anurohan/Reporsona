# RePersona — Visual Technical Documentation

| File | What it is |
|---|---|
| `RePersona_Complete_Visual_Technical_Report.pdf` | The main deliverable: 22 chapters, 49 figures (A4 portrait, landscape pages for large diagrams), clickable table of contents, bookmarks, glossary, abbreviations, references. |
| `RePersona_Interactive_Architecture.html` | Self-contained companion (no network, no dependencies). Open it by double-clicking in any modern browser. |
| `RePersona_Diagram_Sources.zip` | Every figure as a standalone SVG (`diagrams/`) plus the Python generator (`source/`) that produced the PDF. |

## How the PDF and HTML relate
The PDF is the reference. The HTML animates four flows from it: the chat request lifecycle (Ch. 4), the RAG pipeline (Ch. 10), the 15-stage build (Ch. 7) and SSE progress (Ch. 14). Use **Play / Step / Reset**, change speed, and click any component for a description. Dashed nodes are optional integrations. The HTML never contacts a backend; everything is conceptual.

## Accuracy conventions
Badges mark **Implemented**, **Optional**, **Future work**, **Conceptual / hypothetical** and **Unspecified in report**. Wireframes are conceptual, not screenshots. No benchmarks, coverage figures or real model outputs appear. Where the supplied report did not state a detail (e.g. stage-to-module mapping for some stages, chunk size, top-K, exact status codes, column names) the document says so.

## Rebuilding the PDF
`pip install playwright pypdf reportlab && playwright install chromium`, then `python3 source/build.py` (set `OUT` in `lib.py`).
