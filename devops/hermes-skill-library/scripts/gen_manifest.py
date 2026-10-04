#!/usr/bin/env python3
"""Genera MANIFEST.json para la biblioteca de skills de Hermes.

Recorre $HERMES_HOME/skills, identifica cada skill por su SKILL.md, y escribe un
manifiesto con nombre, categoría, tamaño, fecha, hash y archivos de apoyo.

Uso:
    python3 gen_manifest.py                  # escribe MANIFEST.json en el repo
    python3 gen_manifest.py --out /tmp/x.json

Correlo como archivo, nunca como `python3 -c` inline: las comillas anidadas se
rompen y un fallo a medias deja archivos basura.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Directorios que no son skills publicables.
SKIP_DIRS = {".git", ".hub", ".archive", "__pycache__", ".venv", "node_modules"}
# Archivos de estado local, nunca parte de un skill.
SKIP_FILES = {".DS_Store", "MANIFEST.json", "CHANGELOG.txt"}
SKIP_SUFFIX = (".pyc", ".pyo")


def skill_dirs(root: Path) -> list[Path]:
    """Directorios que contienen un SKILL.md, ordenados."""
    out = []
    for md in root.rglob("SKILL.md"):
        if any(part in SKIP_DIRS for part in md.relative_to(root).parts[:-1]):
            continue
        out.append(md.parent)
    return sorted(out)


def parse_frontmatter(md: Path) -> dict:
    """Lee name/description del frontmatter YAML. Best-effort, sin dependencia de yaml."""
    meta: dict = {}
    try:
        lines = md.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return meta
    if not lines or lines[0].strip() != "---":
        return meta
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" in line and not line.startswith((" ", "\t", "-")):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip().strip("'\"")
    return meta


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def dir_size(path: Path) -> int:
    total = 0
    for p in path.rglob("*"):
        if p.is_file() and not any(s in SKIP_SUFFIX for s in p.suffixes):
            if any(part in SKIP_DIRS for part in p.relative_to(path).parts):
                continue
            try:
                total += p.stat().st_size
            except OSError:
                pass
    return total


def support_files(path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    for kind in ("references", "templates", "scripts", "assets"):
        d = path / kind
        if d.is_dir():
            n = sum(1 for f in d.rglob("*") if f.is_file() and not f.name.startswith("._"))
            if n:
                counts[kind] = n
    return counts


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=None, help="ruta de salida (default: <skills>/MANIFEST.json)")
    args = ap.parse_args()

    root = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes")) / "skills"
    if not root.is_dir():
        print(f"ERROR: no existe {root}", file=sys.stderr)
        return 1

    skills = []
    for d in skill_dirs(root):
        md = d / "SKILL.md"
        meta = parse_frontmatter(md)
        rel = d.relative_to(root)
        category = str(rel.parent) if str(rel.parent) != "." else "(raiz)"
        skills.append({
            "name": meta.get("name", d.name),
            "dir": str(rel),
            "category": category,
            "description": meta.get("description", ""),
            "version": meta.get("version", ""),
            "bytes": dir_size(d),
            "skill_md_bytes": md.stat().st_size,
            "skill_md_sha256": sha256(md),
            "modified": datetime.fromtimestamp(
                md.stat().st_mtime, tz=timezone.utc
            ).strftime("%Y-%m-%d"),
            "support_files": support_files(d),
        })

    by_cat: dict[str, int] = {}
    for s in skills:
        by_cat[s["category"]] = by_cat.get(s["category"], 0) + 1

    manifest = {
        "generated": datetime.now().strftime("%Y-%m-%d"),
        "source": str(root),
        "count": len(skills),
        "categories": len(by_cat),
        "total_bytes": sum(s["bytes"] for s in skills),
        "skills_by_category": dict(sorted(by_cat.items())),
        "note": "Generado por devops/hermes-skill-library/scripts/gen_manifest.py",
        "skills": skills,
    }

    out = Path(args.out) if args.out else root / "MANIFEST.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                   encoding="utf-8")
    print(f"{out}: {len(skills)} skills, {len(by_cat)} categorias, "
          f"{manifest['total_bytes'] / 1024:.0f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())