# Xmind Knowledge Maps

A Codex plugin and source-controlled workflow for creating rich, editable Xmind knowledge maps. It supports hierarchical explanations, embedded diagrams, external links, copyable code topics, native LaTeX formulas, and semantic versioning.

The repository also contains versioned example workbooks under `maps/`. Each released map keeps both the ready-to-open `.xmind` file and a diffable source representation.

## What the plugin does

- generates a modern Xmind ZIP/JSON workbook from a readable JSON specification;
- preserves native MathJax formula metadata while embedding a rendered preview;
- keeps code as selectable multiline topic text instead of an image;
- imports existing Xmind workbooks without converting or flattening them;
- detects user edits made in Xmind and commits them before further generation;
- creates map-scoped Git commits and annotated semantic-version tags;
- provides a reusable styled template and extracted theme.

## Requirements

| Dependency | Required for | Notes |
| --- | --- | --- |
| Python 3.9+ | All scripts | Runtime uses only the Python standard library. No PyPI packages are required. |
| Git | Versioned map workflow | Required by `release_map.py`; not required by the standalone builder or inspector. |
| Xmind Desktop | Visual editing and QA | Use a current release that supports ZIP/JSON workbooks and MathJax formula topics. |
| `pdflatex` | Generating formula previews | Usually provided by TeX Live, MacTeX, or MiKTeX. Required only when a generated map contains formulas. |
| `pdftoppm` | Converting formula previews to PNG | Provided by Poppler. Required only when a generated map contains formulas. |
| Codex with plugin support | Automatic skill use | The CLI scripts can also be used without Codex. |

Check the optional formula tools with:

```bash
pdflatex --version
pdftoppm -v
```

## Install as a Codex plugin

Clone the repository, enter its root, and register its local marketplace:

```bash
codex plugin marketplace add "$(pwd)"
codex plugin add xmind-knowledge-maps@xmind-tools
```

Start a new Codex thread after installation so the skill is loaded. The plugin has no external service, account, or authentication dependency.

## Repository layout

```text
.agents/plugins/marketplace.json                  Codex marketplace entry
plugins/xmind-knowledge-maps/
  .codex-plugin/plugin.json                       Plugin manifest
  skills/xmind-knowledge-maps/
    SKILL.md                                      Agent workflow
    agents/openai.yaml                            Skill UI metadata
    assets/default-template.xmind                 Ready-to-open template
    assets/default-template.json                  Editable template specification
    assets/default-theme.json                     Extracted Xmind theme
    assets/workflow-example.png                   Example embedded diagram
    scripts/build_xmind.py                        JSON-to-Xmind builder
    scripts/inspect_xmind.py                      Workbook inspector
    scripts/release_map.py                        Import, sync, build, and release CLI
    references/                                   Format, schema, and versioning details
maps/<slug>/                                      Versioned map sources and artifacts
```

## Create a map

Set a convenience variable from the repository root:

```bash
XMIND_SKILL_DIR="plugins/xmind-knowledge-maps/skills/xmind-knowledge-maps"
```

Copy the editable JSON template and customize it:

```bash
mkdir -p maps/my-topic/assets maps/my-topic/dist
cp "$XMIND_SKILL_DIR/assets/default-template.json" maps/my-topic/map.json
python3 "$XMIND_SKILL_DIR/scripts/release_map.py" prepare my-topic
```

Open `maps/my-topic/dist/my-topic.xmind` in Xmind and visually check it. Then create the first release:

```bash
python3 "$XMIND_SKILL_DIR/scripts/release_map.py" release my-topic --version 1.0.0
```

The ready-to-open styled template is also available at `plugins/xmind-knowledge-maps/skills/xmind-knowledge-maps/assets/default-template.xmind`.
The builder and bundled workbook currently target Xmind's `3/5` data and layout
format identifiers, so newly generated maps do not need an immediate format
migration when opened in Xmind 26.05.

## Import an existing workbook

```bash
python3 "$XMIND_SKILL_DIR/scripts/release_map.py" import my-existing-map /absolute/path/to/map.xmind
```

The original workbook is copied byte for byte into `dist/`. Every archive member is also expanded under `xmind-unpacked/`, which becomes the canonical editable source for imported maps.

## Preserve edits made in Xmind

Before changing a tracked map, run:

```bash
python3 "$XMIND_SKILL_DIR/scripts/release_map.py" sync my-topic
```

The CLI compares a normalized semantic hash and the exact archive hash. If the workbook changed, it commits the workbook and its unpacked source before any generated update can overwrite the edit.

Prepare and release later versions with:

```bash
python3 "$XMIND_SKILL_DIR/scripts/release_map.py" prepare my-topic
python3 "$XMIND_SKILL_DIR/scripts/release_map.py" release my-topic --bump patch
```

Tags use the form `my-topic/v1.0.1`. The CLI never pushes or creates a remote.

## Inspect a workbook

```bash
python3 "$XMIND_SKILL_DIR/scripts/inspect_xmind.py" maps/my-topic/dist/my-topic.xmind
```

The inspector reports sheets, topics, depth, images, formulas, code topics, notes, folded branches, relationships, and packaged resources.

## Validation

```bash
python3 -m py_compile "$XMIND_SKILL_DIR/scripts/"*.py
python3 "$XMIND_SKILL_DIR/scripts/build_xmind.py" \
  "$XMIND_SKILL_DIR/assets/default-template.json" \
  /tmp/xmind-template-check.xmind
python3 "$XMIND_SKILL_DIR/scripts/inspect_xmind.py" /tmp/xmind-template-check.xmind
```

Structural validation cannot replace opening the result in Xmind. Check that formulas remain editable, code remains selectable, images render, folded branches expand, and links point to the intended destinations.

## License

The plugin, scripts, and bundled generic template are available under the MIT License. Existing workbooks and their embedded material under `maps/` are excluded unless a map explicitly states otherwise; see `NOTICE.md`. Xmind is a trademark of Xmind Ltd.; this project is not affiliated with or endorsed by Xmind Ltd. or OpenAI.
