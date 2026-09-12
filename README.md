# Xmind knowledge maps

Versioned sources and ready-to-open Xmind workbooks.

Each map lives under `maps/<map-slug>/`:

```text
map.json                Generated-map specification or native-source descriptor
assets/                 Diagrams and other source assets
dist/<map-slug>.xmind   Built and visually verified workbook
VERSION                 Current semantic version
xmind-unpacked/         Diffable snapshot of Xmind contents and resources
.xmind-state.json       Exact and semantic hashes of the snapshot
.user-edit-pending.json Guard for unreconciled edits in generated maps
```

Release tags are scoped by map, for example `artificial-intelligence/v1.2.0`. A tagged commit contains both the editable source and the finished workbook. This repository is local unless a remote is explicitly configured later.

Before changing an existing source, the Xmind skill compares the workbook with its recorded semantic hash. Manual Xmind edits are unpacked and preserved in a separate Git commit before generated changes continue.

Existing workbooks can be imported without conversion. Their complete `xmind-unpacked/` archive tree is the canonical source, preserving Xmind-specific layout, styles, formulas, links, images, and metadata. The original imported workbook remains byte-identical in `dist/` at its `v1.0.0` tag.
