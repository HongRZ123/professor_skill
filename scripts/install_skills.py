#!/usr/bin/env python3
"""Copy standalone skills; never overwrite existing installations or change app settings."""
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
NAMES = ("professor", "course-tutor")


def install(destination, names=NAMES, source_root=ROOT):
    destination = Path(destination).expanduser().resolve()
    names = tuple(names)
    if not names or len(names) != len(set(names)) or any(name not in NAMES for name in names):
        raise ValueError("Choose distinct known skills")
    plans = []
    for name in names:
        source = source_root / "skills" / name
        target = destination / name
        if not (source / "SKILL.md").is_file():
            raise ValueError("Missing source skill: " + name)
        if target.exists() or target.is_symlink():
            raise FileExistsError("Existing installation preserved: " + str(target))
        for p in source.rglob("*"):
            if p.is_symlink() or not p.resolve().is_relative_to(source.resolve()):
                raise ValueError("Skill source contains a symlink/junction: " + str(p))
        plans.append((source, target))
    destination.mkdir(parents=True, exist_ok=True)
    copied = []
    for source, target in plans:
        # copytree refuses targets created by a competing process after preflight.
        shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo"))
        copied.append(str(target))
    return {"copied": copied, "app_discovery_verified": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    dest = parser.add_mutually_exclusive_group(required=True)
    dest.add_argument("--user", action="store_true", help="Copy into ~/.agents/skills")
    dest.add_argument("--dest", type=Path, help="An explicit skill discovery directory")
    parser.add_argument("--skill", action="append", choices=NAMES)
    a = parser.parse_args()
    try:
        destination = Path.home() / ".agents/skills" if a.user else a.dest
        print(json.dumps(install(destination, a.skill or NAMES), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc), "note": "No existing install is overwritten. Inspect any partial new copy before retrying."}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
