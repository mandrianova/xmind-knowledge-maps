---
name: xmind-knowledge-maps
description: Create, expand, or repair rich editable Xmind knowledge maps with hierarchical explanations, cross-topic relationships, external links, native LaTeX formulas, and embedded diagrams. Use when the user asks for an Xmind or mind map, or when a substantial body of knowledge would be clearer as a navigable visual map; skip simple one-off explanations.
---

# Xmind Knowledge Maps

Create a real editable `.xmind` workbook, not merely a screenshot. Use the bundled reference style by default: clockwise rainbow branches, NeverMind typography, rounded rectangles, green-led accents, compact expandable detail, native formulas, embedded diagrams, external links, and sparse cross-links.

Use `assets/default-template.xmind` as the visual reference and reusable starter workbook. Its editable source specification is `assets/default-template.json`; `assets/default-theme.json` contains the extracted theme.

## Design the knowledge

Organize concepts rather than mirroring chapter order unless the user asks for source navigation. Use major conceptual families as first-level branches. Under each concept, separate definition, purpose, mechanism, worked example, limitations, and comparisons where they add value.

Expand acronyms on first use. Explain every symbol in important formulas. For beginner-facing maps, lead with a concrete example and introduce formal notation afterward. Keep top levels scannable and fold deeper explanatory branches. Follow the language requested for the current map; do not impose English or bilingual content globally.

Keep knowledge on the visible canvas. Avoid notes by default because hidden explanations undermine the map's value. Use a note only when unusually bulky supporting material cannot be shown readably as child topics. For short code examples, use a native multiline `code` topic: it must remain editable and copyable, with monospace styling and a generous width; never substitute a screenshot of code. When the user requests a comprehensive map, supplement supplied material with current primary papers and official documentation. Add useful sources as concise linked topics such as `Original paper ↗` or `Official documentation ↗`, using the topic's external `href`. Keep source branches compact and subordinate to the concept they support.

## Build the workbook

Create a JSON specification following [references/spec-schema.md](references/spec-schema.md), then run:

```bash
python3 scripts/build_xmind.py map.json output.xmind
```

The builder uses `assets/default-theme.json` and automatically validates the modern ZIP/JSON workbook. It embeds PNG diagrams and creates native Xmind MathJax nodes from LaTeX. Read [references/format.md](references/format.md) when diagnosing compatibility or extending the generator.

Use `scripts/inspect_xmind.py` for a new reference workbook. Use `--export-theme` only when the user explicitly wants another style.

## Keep versioned sources

Use the current Git repository as the default source repository. `XMIND_MAPS_REPO` or `--repo /absolute/path` can select another location. Give each map a stable lowercase slug and keep its editable inputs and deliverable together:

```text
maps/<slug>/
├── map.json
├── assets/
├── dist/<slug>.xmind
├── xmind-unpacked/
└── VERSION
```

Write new maps and edits directly in this repository. Do not use the large reference workbooks as working copies. Before releasing, check the repository status and preserve unrelated changes.

When importing an existing workbook, preserve it byte for byte and use the complete unpacked archive as its native editable source:

```bash
python3 scripts/release_map.py import <slug> /absolute/path/to/source.xmind
```

Imported maps use `xmind-unpacked/` as the canonical source and a small `map.json` descriptor. Do not rebuild them through the generated-map schema because that can lose application-specific layout and styling data.

Before changing an existing map's JSON or assets, run:

```bash
python3 scripts/release_map.py sync <slug>
```

The command compares a normalized semantic hash of the workbook with the recorded state. When it detects manual Xmind edits, it preserves the edited workbook, expands its JSON and resources into `xmind-unpacked/`, records exact and semantic hashes, and creates a separate `sync(<slug>): preserve Xmind user edits` commit. For generated maps it also writes a reconciliation marker: inspect the commit and carry visible knowledge changes into `map.json` before generating anything. For imported maps the unpacked tree is already canonical, so no separate reconciliation is needed. `prepare` repeats this guard and stops after preservation rather than overwriting an unrecorded edit.

Build a candidate without committing it:

```bash
python3 scripts/release_map.py prepare <slug>
```

After reconciling a preserved manual edit, acknowledge that step explicitly:

```bash
python3 scripts/release_map.py prepare <slug> --reconciled
```

Do not use `--reconciled` until the user-authored changes have actually been represented in `map.json` and any relevant source assets. The release command refuses to run while the reconciliation marker remains.

Open `maps/<slug>/dist/<slug>.xmind` in Xmind and complete the visual checks below. If Xmind normalizes the file, save that verified copy. Then create the version commit and annotated tag:

```bash
python3 scripts/release_map.py release <slug> --bump patch
```

The first release defaults to `1.0.0`. Use `patch` for corrections and small additions, `minor` for a meaningful new topic family or visual section, and `major` for a fundamental reorganisation. If the user provides a version, pass `--version X.Y.Z`. Tags are map-scoped as `<slug>/vX.Y.Z`. Never push or create a remote unless the user explicitly asks.

Read [references/versioning.md](references/versioning.md) when creating a new map directory, preserving manual Xmind edits, choosing a version bump, recovering a failed release, or inspecting an older version.

## Diagrams and relationships

Create diagrams when they make a process, architecture, state transition, hierarchy, or worked calculation easier to understand. Prefer original clean diagrams with readable labels and few colors. Embed the image beside the concept it explains.

Use visible relationship lines for a few high-value cross-branch links. Dense relationship webs become unreadable when branches expand; represent secondary references as linked topics.

## Verify in Xmind

ZIP validation is not proof that Xmind displays the map correctly. Open the finished file in the installed Xmind app and visibly verify:

- no repair or conversion warning;
- expected topic count and root branches;
- folded branches expand;
- one long explanation wraps readably;
- code blocks remain selectable, copyable, and legible;
- each kind of diagram appears at useful size;
- at least one formula renders and remains editable as a formula;
- relationship lines and the rare note work where used;
- external links open the intended source;
- overview remains navigable at normal zoom.

If Xmind normalizes the file during inspection, preserve the verified copy. Release the verified `.xmind`, its JSON specification, and custom diagrams together through the versioned workflow. State the topic, diagram, code-block, and formula counts, the Xmind version used for the visual check, and the created Git tag.
