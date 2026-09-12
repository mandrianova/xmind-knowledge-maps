# Xmind knowledge maps

Versioned sources and ready-to-open Xmind workbooks.

Each map lives under `maps/<map-slug>/`:

```text
map.json                Editable knowledge-map specification
assets/                 Diagrams and other source assets
dist/<map-slug>.xmind   Built and visually verified workbook
VERSION                 Current semantic version
```

Release tags are scoped by map, for example `artificial-intelligence/v1.2.0`. A tagged commit contains both the editable source and the finished workbook. This repository is local unless a remote is explicitly configured later.
