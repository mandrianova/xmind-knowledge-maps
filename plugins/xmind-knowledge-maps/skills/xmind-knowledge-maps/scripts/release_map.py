#!/usr/bin/env python3
"""Prepare, preserve user edits, and locally release versioned Xmind maps."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import zipfile


SKILL = Path(__file__).resolve().parent.parent
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


def run(*args, cwd, check=True):
    return subprocess.run(args, cwd=cwd, check=check, text=True, capture_output=True)


def default_repository():
    configured = os.environ.get("XMIND_MAPS_REPO")
    if configured:
        return Path(configured).expanduser()
    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=Path.cwd(),
        text=True,
        capture_output=True,
    )
    if result.returncode == 0:
        return Path(result.stdout.strip())
    return Path.cwd()


def ensure_repository(repo):
    if not repo.is_dir() or not (repo / ".git").is_dir():
        raise SystemExit(f"Not an initialized Git repository: {repo}")


def paths_for(repo, slug):
    if not SLUG.fullmatch(slug):
        raise SystemExit("Slug must contain lowercase letters, digits, and single hyphens")
    map_dir = repo / "maps" / slug
    return map_dir, map_dir / "map.json", map_dir / "dist" / f"{slug}.xmind"


def json_file(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def archive_hash(workbook):
    digest = hashlib.sha256()
    with workbook.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def semantic_hash(workbook):
    digest = hashlib.sha256()
    with zipfile.ZipFile(workbook) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
        names = [name for name in archive.namelist() if name == "content.json" or name.startswith("resources/")]
        for name in sorted(name for name in names if not name.endswith("/")):
            data = archive.read(name)
            if name.endswith(".json"):
                try:
                    data = json.dumps(json.loads(data), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                except json.JSONDecodeError:
                    pass
            digest.update(name.encode("utf-8") + b"\0" + data + b"\0")
    return digest.hexdigest()


def workbook_state(workbook):
    return {
        "semantic_sha256": semantic_hash(workbook),
        "archive_sha256": archive_hash(workbook),
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    }


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def source_mode(map_dir):
    spec = json_file(map_dir / "map.json") or {}
    return spec.get("source_mode", "generated-json")


def validate_workbook(workbook):
    if not workbook.is_file():
        raise SystemExit(f"Prepared workbook does not exist: {workbook}")
    command = [sys.executable, str(SKILL / "scripts" / "build_xmind.py"), str(workbook), str(workbook), "--validate-only"]
    result = subprocess.run(command, text=True, capture_output=True)
    if result.returncode:
        raise SystemExit(result.stderr or result.stdout)
    print(result.stdout.strip())


def validate_native_workbook(workbook):
    if not workbook.is_file():
        raise SystemExit(f"Native workbook does not exist: {workbook}")
    with zipfile.ZipFile(workbook) as archive:
        bad = archive.testzip()
        if bad:
            raise SystemExit(f"Corrupt ZIP member: {bad}")
        try:
            content = json.loads(archive.read("content.json"))
        except KeyError:
            raise SystemExit("Native workbook has no content.json")
        except json.JSONDecodeError as error:
            raise SystemExit(f"Invalid content.json: {error}")
    sheets = content if isinstance(content, list) else [content]
    if not sheets or any(not isinstance(sheet, dict) or not isinstance(sheet.get("rootTopic"), dict) for sheet in sheets):
        raise SystemExit("Native workbook has no valid root topic")

    counts = {"topics": 0, "images": 0, "formulas": 0}

    def walk(node):
        counts["topics"] += 1
        if "image" in node:
            counts["images"] += 1
            if node.get("image", {}).get("isMathJaxImage"):
                counts["formulas"] += 1
        for group in node.get("children", {}).values():
            if isinstance(group, list):
                for child in group:
                    if isinstance(child, dict):
                        walk(child)

    for sheet in sheets:
        walk(sheet["rootTopic"])
    print(
        f"Valid native: sheets={len(sheets)}, topics={counts['topics']}, "
        f"images={counts['images']}, formulas={counts['formulas']}"
    )


def unpack_workbook(workbook, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="xmind-unpacked-", dir=destination.parent) as temporary:
        staging = Path(temporary)
        staging_root = staging.resolve()
        with zipfile.ZipFile(workbook) as archive:
            for name in archive.namelist():
                if name.endswith("/"):
                    continue
                target = (staging / name).resolve()
                if not target.is_relative_to(staging_root):
                    raise SystemExit(f"Unsafe workbook member: {name}")
                target.parent.mkdir(parents=True, exist_ok=True)
                data = archive.read(name)
                if name.endswith(".json"):
                    try:
                        value = json.loads(data)
                        data = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
                    except json.JSONDecodeError:
                        pass
                target.write_bytes(data)
        previous = None
        if destination.exists():
            previous = Path(tempfile.mkdtemp(prefix=f".{destination.name}-previous-", dir=destination.parent))
            previous.rmdir()
            destination.replace(previous)
        try:
            shutil.copytree(staging, destination)
        except Exception:
            shutil.rmtree(destination, ignore_errors=True)
            if previous and previous.exists():
                previous.replace(destination)
            raise
        finally:
            if previous and previous.exists():
                shutil.rmtree(previous, ignore_errors=True)


def pack_workbook(source, workbook):
    if not source.is_dir() or not (source / "content.json").is_file():
        raise SystemExit(f"Missing native Xmind source: {source}")
    workbook.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(prefix="xmind-pack-", suffix=".xmind", dir=workbook.parent, delete=False) as handle:
        temporary = Path(handle.name)
    try:
        with zipfile.ZipFile(temporary, "w") as archive:
            for path in sorted(item for item in source.rglob("*") if item.is_file()):
                name = path.relative_to(source).as_posix()
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_STORED if name == "mimetype" else zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                archive.writestr(info, path.read_bytes())
        temporary.replace(workbook)
    finally:
        temporary.unlink(missing_ok=True)


def snapshot_workbook(map_dir, workbook):
    if source_mode(map_dir) == "xmind-unpacked":
        validate_native_workbook(workbook)
    else:
        validate_workbook(workbook)
    unpack_workbook(workbook, map_dir / "xmind-unpacked")
    state = workbook_state(workbook)
    write_json(map_dir / ".xmind-state.json", state)
    (map_dir / ".candidate-state.json").unlink(missing_ok=True)
    return state


def dirty_paths(repo):
    result = run("git", "status", "--porcelain", "--untracked-files=all", cwd=repo)
    paths = []
    for line in result.stdout.splitlines():
        if len(line) >= 4:
            paths.append(line[3:].split(" -> ")[-1].strip('"'))
    return paths


def expected_hash(map_dir):
    for name in (".candidate-state.json", ".xmind-state.json"):
        state = json_file(map_dir / name)
        if state and state.get("semantic_sha256"):
            yield state["semantic_sha256"]


def sync_user_edits(repo, slug):
    map_dir, _, workbook = paths_for(repo, slug)
    if not workbook.exists():
        print(f"No existing workbook to sync: {workbook}")
        return False
    current = semantic_hash(workbook)
    if current in set(expected_hash(map_dir)):
        print("No unrecorded Xmind edits detected")
        return False

    relative_workbook = workbook.relative_to(repo).as_posix()
    unexpected = [path for path in dirty_paths(repo) if path != relative_workbook]
    if unexpected:
        formatted = "\n".join(f"  {path}" for path in unexpected)
        raise SystemExit(f"Cannot isolate Xmind user edits while other changes exist:\n{formatted}")

    state = snapshot_workbook(map_dir, workbook)
    if source_mode(map_dir) == "xmind-unpacked":
        (map_dir / ".user-edit-pending.json").unlink(missing_ok=True)
    else:
        write_json(
            map_dir / ".user-edit-pending.json",
            {
                "semantic_sha256": state["semantic_sha256"],
                "preserved_at": state["recorded_at"],
                "instruction": "Reconcile xmind-unpacked/content.json into map.json before preparing a new build",
            },
        )
    relative_map = f"maps/{slug}"
    run("git", "add", "--", relative_map, cwd=repo)
    changed = run("git", "diff", "--cached", "--quiet", "--", relative_map, cwd=repo, check=False)
    if changed.returncode == 0:
        raise SystemExit("Workbook hash changed but no Git changes were produced")
    if changed.returncode != 1:
        raise SystemExit("Unable to inspect staged Xmind edits")
    run("git", "commit", "-m", f"sync({slug}): preserve Xmind user edits", "--", relative_map, cwd=repo)
    commit = run("git", "rev-parse", "--short", "HEAD", cwd=repo).stdout.strip()
    print(f"Preserved user edits in commit {commit}")
    print(f"Semantic SHA-256: {state['semantic_sha256']}")
    print(f"Unpacked source: {map_dir / 'xmind-unpacked'}")
    return True


def prepare(repo, slug, reconciled=False):
    if sync_user_edits(repo, slug):
        if source_mode(repo / "maps" / slug) == "xmind-unpacked":
            raise SystemExit("User edits were preserved as the native source. Apply new changes, then run prepare again.")
        raise SystemExit(
            "User edits were preserved before generation. Reconcile the latest "
            "xmind-unpacked/content.json changes into map.json, then run prepare again."
        )
    map_dir, spec, workbook = paths_for(repo, slug)
    pending = map_dir / ".user-edit-pending.json"
    if pending.exists() and not reconciled:
        raise SystemExit(
            f"Preserved user edits still require reconciliation: {pending}\n"
            "Update map.json from xmind-unpacked/content.json, then rerun prepare with --reconciled."
        )
    if reconciled:
        pending.unlink(missing_ok=True)
    if not spec.is_file():
        raise SystemExit(f"Missing map specification: {spec}")
    workbook.parent.mkdir(parents=True, exist_ok=True)
    if source_mode(map_dir) == "xmind-unpacked":
        pack_workbook(map_dir / "xmind-unpacked", workbook)
        validate_native_workbook(workbook)
        result_text = "Packed and validated native Xmind source"
    else:
        command = [sys.executable, str(SKILL / "scripts" / "build_xmind.py"), str(spec), str(workbook)]
        result = subprocess.run(command, text=True, capture_output=True)
        if result.returncode:
            raise SystemExit(result.stderr or result.stdout)
        result_text = result.stdout.strip()
    write_json(map_dir / ".candidate-state.json", workbook_state(workbook))
    print(result_text)
    print(f"Prepared: {workbook}")
    print("Open this workbook in Xmind, complete visual QA, save it, then run release.")


def parse_version(value):
    match = SEMVER.fullmatch(value.strip().removeprefix("v"))
    if not match:
        raise SystemExit(f"Invalid semantic version: {value!r}")
    return tuple(map(int, match.groups()))


def next_version(map_dir, explicit, bump):
    if explicit:
        return ".".join(map(str, parse_version(explicit)))
    version_file = map_dir / "VERSION"
    if not version_file.exists():
        return "1.0.0"
    major, minor, patch = parse_version(version_file.read_text(encoding="utf-8"))
    if bump == "major":
        major, minor, patch = major + 1, 0, 0
    elif bump == "minor":
        minor, patch = minor + 1, 0
    else:
        patch += 1
    return f"{major}.{minor}.{patch}"


def release(repo, slug, explicit, bump, message):
    map_dir, spec, workbook = paths_for(repo, slug)
    if not spec.is_file():
        raise SystemExit(f"Missing map specification: {spec}")
    if (map_dir / ".user-edit-pending.json").exists():
        raise SystemExit("User edits have not been reconciled into map.json; release refused")
    if source_mode(map_dir) == "xmind-unpacked":
        validate_native_workbook(workbook)
    else:
        validate_workbook(workbook)

    allowed = f"maps/{slug}/"
    unrelated = [path for path in dirty_paths(repo) if not path.startswith(allowed)]
    if unrelated:
        formatted = "\n".join(f"  {path}" for path in unrelated)
        raise SystemExit(f"Unrelated repository changes must be resolved first:\n{formatted}")

    version = next_version(map_dir, explicit, bump)
    tag = f"{slug}/v{version}"
    exists = run("git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}", cwd=repo, check=False)
    if exists.returncode == 0:
        raise SystemExit(f"Tag already exists: {tag}")

    snapshot_workbook(map_dir, workbook)
    (map_dir / "VERSION").write_text(version + "\n", encoding="utf-8")
    run("git", "add", "--", allowed.rstrip("/"), cwd=repo)
    changed = run("git", "diff", "--cached", "--quiet", "--", allowed.rstrip("/"), cwd=repo, check=False)
    if changed.returncode == 0:
        raise SystemExit("Nothing changed; release was not created")
    if changed.returncode != 1:
        raise SystemExit("Unable to inspect staged release changes")

    commit_message = message or f"release({slug}): v{version}"
    run("git", "commit", "-m", commit_message, "--", allowed.rstrip("/"), cwd=repo)
    run("git", "tag", "-a", tag, "-m", f"{slug} v{version}", cwd=repo)
    commit = run("git", "rev-parse", "--short", "HEAD", cwd=repo).stdout.strip()
    print(f"Released: {tag}")
    print(f"Commit: {commit}")
    print(f"Workbook: {workbook}")


def import_workbook(repo, slug, source, explicit):
    map_dir, spec, workbook = paths_for(repo, slug)
    if map_dir.exists():
        raise SystemExit(f"Map already exists: {map_dir}")
    if dirty_paths(repo):
        raise SystemExit("Repository must be clean before importing a workbook")
    source = source.expanduser().resolve()
    validate_native_workbook(source)
    version = ".".join(map(str, parse_version(explicit or "1.0.0")))
    tag = f"{slug}/v{version}"
    exists = run("git", "rev-parse", "--verify", "--quiet", f"refs/tags/{tag}", cwd=repo, check=False)
    if exists.returncode == 0:
        raise SystemExit(f"Tag already exists: {tag}")

    title = slug
    sheet_count = 0
    with zipfile.ZipFile(source) as archive:
        content = json.loads(archive.read("content.json"))
        sheets = content if isinstance(content, list) else [content]
        sheet_count = len(sheets)
        if sheets:
            title = sheets[0].get("rootTopic", {}).get("title") or sheets[0].get("title") or title

    workbook.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, workbook)
    spec.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        spec,
        {
            "source_mode": "xmind-unpacked",
            "title": title,
            "sheet_count": sheet_count,
            "original_filename": source.name,
            "workbook": f"dist/{slug}.xmind",
            "native_source": "xmind-unpacked",
        },
    )
    snapshot_workbook(map_dir, workbook)
    (map_dir / "VERSION").write_text(version + "\n", encoding="utf-8")

    relative_map = f"maps/{slug}"
    run("git", "add", "--", relative_map, cwd=repo)
    run("git", "commit", "-m", f"import({slug}): v{version}", "--", relative_map, cwd=repo)
    run("git", "tag", "-a", tag, "-m", f"{slug} v{version}", cwd=repo)
    commit = run("git", "rev-parse", "--short", "HEAD", cwd=repo).stdout.strip()
    state = json_file(map_dir / ".xmind-state.json")
    print(f"Imported: {tag}")
    print(f"Commit: {commit}")
    print(f"Title: {title}")
    print(f"Sheets: {sheet_count}")
    print(f"Archive SHA-256: {state['archive_sha256']}")
    print(f"Workbook: {workbook}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repo",
        type=Path,
        help="Map repository (default: XMIND_MAPS_REPO or the current Git root)",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    sync_parser = subparsers.add_parser("sync")
    sync_parser.add_argument("slug")
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("slug")
    import_parser.add_argument("workbook", type=Path)
    import_parser.add_argument("--version", default="1.0.0")
    prepare_parser = subparsers.add_parser("prepare")
    prepare_parser.add_argument("slug")
    prepare_parser.add_argument("--reconciled", action="store_true")
    release_parser = subparsers.add_parser("release")
    release_parser.add_argument("slug")
    version_group = release_parser.add_mutually_exclusive_group()
    version_group.add_argument("--version")
    version_group.add_argument("--bump", choices=("patch", "minor", "major"), default="patch")
    release_parser.add_argument("--message")
    args = parser.parse_args()
    repo = (args.repo or default_repository()).expanduser().resolve()
    ensure_repository(repo)
    if args.command == "sync":
        sync_user_edits(repo, args.slug)
    elif args.command == "import":
        import_workbook(repo, args.slug, args.workbook, args.version)
    elif args.command == "prepare":
        prepare(repo, args.slug, args.reconciled)
    else:
        release(repo, args.slug, args.version, args.bump, args.message)


if __name__ == "__main__":
    main()
