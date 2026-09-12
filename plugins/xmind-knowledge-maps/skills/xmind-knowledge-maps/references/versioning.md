# Versioned map workspace

The CLI uses `XMIND_MAPS_REPO` when set, otherwise the current Git repository. Pass `--repo /absolute/path` to override either choice. The repository stores source material and assets beside the built workbook so every tagged commit is reproducible and immediately usable. Generated maps use `map.json`; imported workbooks use the complete `xmind-unpacked/` tree as their native source.

## Create a map

Choose a stable lowercase slug with letters, digits, and hyphens. Create:

```text
maps/<slug>/map.json
maps/<slug>/assets/
maps/<slug>/dist/
maps/<slug>/xmind-unpacked/
maps/<slug>/.xmind-state.json
```

Use paths such as `assets/diagram.png` inside `map.json`. The builder resolves them relative to the specification.

## Preserve manual Xmind edits

Before editing `map.json` or any generated asset for an existing map, run:

```bash
python3 scripts/release_map.py sync <slug>
```

The exact archive hash detects byte-for-byte changes. The semantic hash normalizes `content.json` and includes embedded resources, avoiding false changes from ZIP ordering while still detecting knowledge, style, layout, formula, link, and image changes.

If the workbook changed, `sync` expands every archive member under `xmind-unpacked/`, updates `.xmind-state.json`, writes `.user-edit-pending.json`, and creates a separate preservation commit. Inspect the commit diff, especially `xmind-unpacked/content.json`, and carry the relevant changes into `map.json`. Do not generate over the workbook before this reconciliation. If other working-tree changes already exist, synchronization stops because it cannot safely attribute them to the user's Xmind edit.

For an imported native workbook, `xmind-unpacked/` is already the canonical editable source. In that mode `sync` commits the complete user edit directly and does not create a reconciliation marker.

`prepare` runs the same check. When it finds edits, it commits them and exits before rebuilding the workbook. After the reconciliation is complete, run `prepare <slug> --reconciled`; this removes the marker and builds the candidate. `release` refuses to proceed while the marker exists.

## Prepare and release

From the skill directory, run:

```bash
python3 scripts/release_map.py prepare <slug>
```

This builds and structurally validates `maps/<slug>/dist/<slug>.xmind` without touching Git history. Open that exact output in Xmind, inspect it, and save any Xmind normalization before releasing.

Then run one of:

```bash
python3 scripts/release_map.py release <slug> --bump patch
python3 scripts/release_map.py release <slug> --bump minor
python3 scripts/release_map.py release <slug> --bump major
python3 scripts/release_map.py release <slug> --version 2.0.0
```

The release command validates the existing workbook, saves a diffable unpacked snapshot and both hashes, updates `VERSION`, stages only `maps/<slug>`, commits it, and creates an annotated `<slug>/vX.Y.Z` tag. It refuses duplicate tags, an unchanged release, or dirty paths elsewhere in the repository. It never pushes.

## Version meaning

- `patch`: corrections, wording improvements, source updates, small examples, and layout fixes.
- `minor`: a new conceptual branch, substantial new examples, or a meaningful new diagram set.
- `major`: a new ontology, incompatible restructuring, or a deliberate reset of how the subject is organised.

For a brand-new map, the first release is `1.0.0` unless the user specifies another version.

## Import an existing workbook

Import a known-good `.xmind` file without rebuilding it:

```bash
python3 scripts/release_map.py import example-map /absolute/path/to/example.xmind
```

The import preserves the original workbook byte for byte in `dist/`, expands every archive member into `xmind-unpacked/`, creates a small `map.json` descriptor, records both hashes, commits the map, and creates `<slug>/v1.0.0`. Future source edits are made in `xmind-unpacked/`; `prepare` repacks that tree into the workbook.

## Inspect history

```bash
git log --oneline --decorate -- maps/<slug>
git tag --list '<slug>/v*' --sort=-version:refname
git show '<slug>/v1.0.0:maps/<slug>/map.json'
```

To recover from a release failure, inspect `git status` first. Do not reset or delete user changes automatically. Fix the reported condition and rerun `release`; the tag is created only after the commit succeeds.
