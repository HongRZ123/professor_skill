#!/usr/bin/env python3
"""Build portable release archives outside the source tree without overwriting releases."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile
from validate_library import ROOT, files, validate


def build(out, root=ROOT):
    root, out = root.resolve(), Path(out).expanduser().resolve()
    if out == root or out.is_relative_to(root):
        raise ValueError("Release directory must be outside the source/plugin tree")
    result = validate(root)
    if not result["ok"]:
        raise ValueError("Library validation failed: " + json.dumps(result["errors"], ensure_ascii=False))
    manifest = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
    version, name = manifest["version"], manifest["name"]
    all_files = list(files(root))
    source = [(p, name + "/" + p.relative_to(root).as_posix()) for p in all_files]
    # Keep linked end-user docs with the plugin, but omit development utilities and tests.
    plugin = [(p, arc) for p, arc in source if p.relative_to(root).parts[0] in {"plugin.json", "skills", "README.md", "LICENSE", "docs"}
              or p.relative_to(root).as_posix() == "scripts/install_skills.py"]
    packages = {f"{name}-{version}-source.zip": source, f"{name}-{version}-plugin.zip": plugin}
    for skill in ("professor", "course-tutor"):
        base = root / "skills" / skill
        packages[f"{skill}-{version}.zip"] = [(p, skill + "/" + p.relative_to(base).as_posix()) for p in all_files if p.is_relative_to(base)]
    targets = [out / filename for filename in packages] + [out / "SHA256SUMS"]
    if any(p.exists() for p in targets):
        raise FileExistsError("Existing release preserved; choose a fresh output directory or new version")
    out.mkdir(parents=True, exist_ok=True)
    hashes = []
    for filename, entries in packages.items():
        target = out / filename
        with zipfile.ZipFile(target, "x", compression=zipfile.ZIP_DEFLATED) as archive:
            for p, arcname in entries:
                archive.write(p, arcname)
        with zipfile.ZipFile(target) as archive:
            if archive.testzip():
                raise ValueError("CRC verification failed: " + filename)
        hashes.append(hashlib.sha256(target.read_bytes()).hexdigest() + "  " + filename)
    with (out / "SHA256SUMS").open("x", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(hashes) + "\n")
    return {"output": str(out), "archives": list(packages), "checksums": "SHA256SUMS"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT.parent / (ROOT.name + "-dist"))
    a = p.parse_args()
    try:
        print(json.dumps(build(a.out), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
