#!/usr/bin/env python3
"""Inspect a modern Xmind ZIP/JSON workbook without modifying it."""
import argparse
import json
from pathlib import Path
import zipfile


def walk(topic, depth=0):
    yield depth, topic
    for child in topic.get("children", {}).get("attached", []):
        yield from walk(child, depth + 1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--export-theme", type=Path)
    args = parser.parse_args()
    with zipfile.ZipFile(args.workbook) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
        content = json.loads(archive.read("content.json"))
        print(f"Workbook: {args.workbook}\nSheets: {len(content)}")
        for index, sheet in enumerate(content, 1):
            nodes = list(walk(sheet["rootTopic"]))
            images = sum("image" in node for _, node in nodes)
            formulas = sum(any(ext.get("provider") == "org.xmind.ui.mathJax" for ext in node.get("extensions", [])) for _, node in nodes)
            code_blocks = sum("monospace" in node.get("style", {}).get("properties", {}).get("fo:font-family", "") for _, node in nodes)
            folded = sum(node.get("branch") == "folded" for _, node in nodes)
            notes = sum("notes" in node for _, node in nodes)
            print(f"[{index}] {sheet.get('title', '')!r}: root={sheet['rootTopic'].get('title', '')!r}, topics={len(nodes)}, max_depth={max(depth for depth, _ in nodes)}, images={images}, formulas={formulas}, code_blocks={code_blocks}, notes={notes}, folded={folded}, relationships={len(sheet.get('relationships', []))}")
        resources = [name for name in archive.namelist() if name.startswith("resources/") and not name.endswith("/")]
        print(f"Resources: {len(resources)}")
        if args.export_theme:
            theme = content[0].get("theme")
            if not theme:
                raise SystemExit("First sheet has no theme")
            args.export_theme.write_text(json.dumps(theme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(f"Theme exported to {args.export_theme}")


if __name__ == "__main__":
    main()
