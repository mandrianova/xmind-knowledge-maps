#!/usr/bin/env python3
"""Build and structurally validate a modern Xmind workbook from JSON."""
import argparse
import hashlib
import html
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import uuid
import zipfile

SKILL = Path(__file__).resolve().parent.parent


def stable_id(seed):
    return uuid.uuid5(uuid.NAMESPACE_URL, "xmind-knowledge-maps/" + seed).hex


def image_size(path):
    data = path.read_bytes()
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return struct.unpack(">II", data[16:24])
    if data.startswith((b"GIF87a", b"GIF89a")):
        return struct.unpack("<HH", data[6:10])
    if data.startswith(b"\xff\xd8"):
        pos = 2
        while pos + 9 < len(data):
            if data[pos] != 0xFF:
                pos += 1
                continue
            marker = data[pos + 1]
            pos += 2
            if marker in (0xD8, 0xD9):
                continue
            length = int.from_bytes(data[pos:pos + 2], "big")
            if marker in range(0xC0, 0xC4):
                return int.from_bytes(data[pos + 5:pos + 7], "big"), int.from_bytes(data[pos + 3:pos + 5], "big")
            pos += length
    raise ValueError(f"Unsupported image: {path}")


def render_formula(tex, output):
    pdflatex = shutil.which("pdflatex")
    pdftoppm = shutil.which("pdftoppm")
    if not pdflatex or not pdftoppm:
        raise RuntimeError("Native formula rendering requires pdflatex and pdftoppm")
    document = """\\documentclass[border=5pt]{standalone}
\\usepackage{amsmath,amssymb,xcolor}
\\begin{document}
\\color[HTML]{18372F}$\\displaystyle %s$
\\end{document}
""" % tex
    with tempfile.TemporaryDirectory(prefix="xmind-formula-") as directory:
        work = Path(directory)
        (work / "formula.tex").write_text(document, encoding="utf-8")
        result = subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error", "formula.tex"], cwd=work, capture_output=True, text=True)
        if result.returncode:
            tail = "\n".join(result.stdout.splitlines()[-15:])
            raise RuntimeError(f"Invalid LaTeX {tex!r}:\n{tail}")
        subprocess.run([pdftoppm, "-png", "-singlefile", "-r", "180", str(work / "formula.pdf"), str(work / "formula")], check=True, capture_output=True)
        output.write_bytes((work / "formula.png").read_bytes())


def build(spec_path, output):
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    base = spec_path.parent
    if not spec.get("title") or not isinstance(spec.get("topics"), list):
        raise ValueError("Specification requires title and topics")
    theme_path = base / spec["theme_file"] if spec.get("theme_file") else SKILL / "assets" / "default-theme.json"
    theme = json.loads(theme_path.read_text(encoding="utf-8"))
    resources, keys = {}, {}
    fold_depth = spec.get("fold_depth", 3)

    def add_resource(path):
        data = path.read_bytes()
        name = "resources/" + hashlib.sha256(data).hexdigest() + (path.suffix.lower() or ".png")
        resources[name] = data
        return name

    def make_notes(item):
        plain = item.get("notes", "")
        markup = item.get("notes_html") or (f"<p>{html.escape(plain)}</p>" if plain else "")
        for source in item.get("sources", []):
            title, url = source["title"], source["url"]
            plain += ("\n\n" if plain else "") + f"{title}\n{url}"
            markup += f'<p><a href="{html.escape(url)}">{html.escape(title)}</a></p>'
        return {"plain": {"content": plain}, "realHTML": {"content": markup}} if plain or markup else None

    def make_topic(item, trail, depth):
        content_fields = [field for field in ("title", "formula", "code") if field in item]
        if len(content_fields) != 1:
            raise ValueError(f"Topic {trail} needs exactly one of title, formula, or code")
        key = item.get("key")
        node = {"id": stable_id(key or trail), "class": "topic", "title": item.get("title", item.get("code", ""))}
        if key:
            if key in keys:
                raise ValueError(f"Duplicate key: {key}")
            keys[key] = node
        notes = make_notes(item)
        if notes:
            node["notes"] = notes
        if item.get("href"):
            node["href"] = item["href"]
        if "code" in item:
            node["customWidth"] = item.get("width", 560)
            node["style"] = {
                "id": stable_id("code-style/" + (key or trail)),
                "properties": {
                    "fo:font-family": "'SFMono-Regular','Menlo','Monaco','Consolas','monospace'",
                    "fo:font-size": item.get("font_size", "11pt"),
                    "fo:font-weight": "400",
                    "fo:font-style": "normal",
                    "fo:color": "#18372F",
                    "fo:text-align": "left",
                    "svg:fill": "#F3F8F5",
                    "fill-pattern": "solid",
                    "border-line-color": "#A6D8C3",
                    "border-line-width": "1pt",
                    "shape-class": "org.xmind.topicShape.roundedRect"
                }
            }
        elif "formula" in item:
            tex = item["formula"]
            node["title"] = item.get("caption", "")
            if node["title"]:
                node["customWidth"] = item.get("width", 380)
            with tempfile.TemporaryDirectory(prefix="xmind-png-") as directory:
                image_path = Path(directory) / "formula.png"
                render_formula(tex, image_path)
                width, height = image_size(image_path)
                resource = add_resource(image_path)
            display_width = min(item.get("image_width", 600), width)
            node["image"] = {"src": "xap:" + resource, "width": display_width, "height": round(height * display_width / width), "isMathJaxImage": True}
            node["extensions"] = [{"provider": "org.xmind.ui.mathJax", "content": {"content": tex}}]
        elif item.get("image"):
            image_path = (base / item["image"]).resolve()
            width, height = image_size(image_path)
            display_width = min(item.get("image_width", 560), width)
            node["image"] = {"src": "xap:" + add_resource(image_path), "width": display_width, "height": round(height * display_width / width)}
        children = [make_topic(child, f"{trail}/{index}", depth + 1) for index, child in enumerate(item.get("children", []))]
        if children:
            node["children"] = {"attached": children}
            if item.get("folded", depth >= fold_depth):
                node["branch"] = "folded"
        return node

    root = {"id": stable_id("root/" + spec["title"]), "class": "topic", "title": spec["title"], "structureClass": spec.get("structure", "org.xmind.ui.map.clockwise")}
    root["children"] = {"attached": [make_topic(item, f"root/{index}", 1) for index, item in enumerate(spec["topics"])]}
    relations = []
    for index, relation in enumerate(spec.get("relationships", [])):
        if relation["from"] not in keys or relation["to"] not in keys:
            raise ValueError(f"Unknown relationship endpoint: {relation}")
        relations.append({"id": stable_id(f"relation/{index}"), "end1Id": keys[relation["from"]]["id"], "end2Id": keys[relation["to"]]["id"], "title": relation.get("label", "")})
    sheet_id = stable_id("sheet/" + spec.get("sheet_title", spec["title"]))
    sheet = {"id": sheet_id, "class": "sheet", "title": spec.get("sheet_title", spec["title"]), "rootTopic": root, "theme": theme}
    if relations:
        sheet["relationships"] = relations
    metadata = {"dataStructureVersion": "2", "layoutEngineVersion": "3", "activeSheetId": sheet_id, "creator": {"name": "xmind-knowledge-maps", "version": "1"}}
    files = {"content.json": json.dumps([sheet], ensure_ascii=False).encode(), "metadata.json": json.dumps(metadata).encode(), **resources}
    files["manifest.json"] = json.dumps({"file-entries": {name: {} for name in files}}).encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    return validate(output)


def validate(path):
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        content = json.loads(archive.read("content.json"))
        manifest = json.loads(archive.read("manifest.json"))["file-entries"]
        assert set(manifest) <= set(archive.namelist())
        ids, images, formulas, code_blocks = [], 0, 0, 0
        def walk(node):
            nonlocal images, formulas, code_blocks
            ids.append(node["id"])
            assert node.get("title") or "image" in node
            if "image" in node:
                images += 1
                assert node["image"]["src"].removeprefix("xap:") in manifest
            formulas += any(ext.get("provider") == "org.xmind.ui.mathJax" for ext in node.get("extensions", []))
            font = node.get("style", {}).get("properties", {}).get("fo:font-family", "")
            code_blocks += "monospace" in font
            for child in node.get("children", {}).get("attached", []):
                walk(child)
        for sheet in content:
            walk(sheet["rootTopic"])
        assert len(ids) == len(set(ids))
        for sheet in content:
            for relation in sheet.get("relationships", []):
                assert relation["end1Id"] in ids and relation["end2Id"] in ids
        return len(ids), images, formulas, code_blocks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    counts = validate(args.output) if args.validate_only else build(args.spec.resolve(), args.output.resolve())
    print(f"Valid: topics={counts[0]}, images={counts[1]}, formulas={counts[2]}, code_blocks={counts[3]}")


if __name__ == "__main__":
    main()
