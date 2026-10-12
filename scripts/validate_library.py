#!/usr/bin/env python3
"""Check distributable structure and local references, not teaching behavior."""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote
import yaml

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE = {"build", "dist", ".git", "__pycache__", ".venv"}


def files(root):
    for p in sorted(root.rglob("*")):
        relative = p.relative_to(root)
        if any(part in EXCLUDE for part in relative.parts) or p.suffix in {".pyc", ".pyo", ".zip"}:
            continue
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            raise ValueError("Nonportable symlink/junction: " + str(relative))
        if p.is_file():
            yield p


def local_targets(path):
    body = re.sub(r"```.*?```", "", path.read_text(encoding="utf-8"), flags=re.S)
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", body):
        target = target.strip("<>").split("#", 1)[0]
        if target and not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            yield (path.parent / unquote(target)).resolve()


def validate(root=ROOT, schema=None):
    root = root.resolve()
    errors, counts = [], {"skills": 0, "markdown_files": 0, "local_links": 0, "candidate_questions": 0}
    try:
        all_files = list(files(root))
        manifest = json.loads((root / "plugin.json").read_text(encoding="utf-8"))
        if manifest.get("name") != "deep-learning-skills" or not re.fullmatch(r"\d+\.\d+\.\d+", manifest.get("version", "")):
            errors.append("Invalid plugin identity/version")
        if manifest.get("$schema") != "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json":
            errors.append("Missing portable schema declaration")
        if any(k in manifest for k in ("skills", "mcpServers", "apps", "interface")):
            errors.append("Legacy fields at portable manifest root")
        interface = manifest.get("extensions", {}).get("com.openai", {}).get("interface", {})
        if not 1 <= len(interface.get("shortDescription", "")) <= 30:
            errors.append("Plugin subtitle must contain 1-30 characters")
        if schema:
            import jsonschema
            jsonschema.validate(manifest, json.loads(Path(schema).read_text(encoding="utf-8")))
        for skill in sorted((root / "skills").iterdir()):
            if not skill.is_dir():
                continue
            counts["skills"] += 1
            text = (skill / "SKILL.md").read_text(encoding="utf-8")
            front = re.match(r"\A---\r?\n(.*?)\r?\n---(?:\r?\n|$)", text, re.S)
            if not front:
                errors.append(f"{skill.name}: missing YAML frontmatter")
                continue
            meta = yaml.safe_load(front.group(1))
            if meta.get("name") != skill.name or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", skill.name):
                errors.append(f"{skill.name}: name mismatch")
            description = meta.get("description", "")
            if not isinstance(description, str) or not 1 <= len(description) <= 1024:
                errors.append(f"{skill.name}: invalid description")
            ui = yaml.safe_load((skill / "agents/openai.yaml").read_text(encoding="utf-8"))["interface"]
            if not 25 <= len(ui.get("short_description", "")) <= 64 or "$" + skill.name not in ui.get("default_prompt", ""):
                errors.append(f"{skill.name}: invalid UI metadata")
            # Every Markdown reference must be reachable from this independent skill.
            reachable, pending = set(), [skill / "SKILL.md"]
            while pending:
                current = pending.pop().resolve()
                if current in reachable or not current.is_file() or current.suffix != ".md":
                    continue
                reachable.add(current)
                for target in local_targets(current):
                    if target.is_relative_to(skill.resolve()):
                        pending.append(target)
                    else:
                        errors.append(f"{skill.name}: runtime dependency outside skill: {target}")
            for reference in (skill / "references").rglob("*.md"):
                if reference.resolve() not in reachable:
                    errors.append(f"Unreachable reference: {reference.relative_to(root)}")
        for path in all_files:
            if path.suffix != ".md":
                continue
            counts["markdown_files"] += 1
            text = path.read_text(encoding="utf-8")
            if "C:/Users/" in text or "C:\\Users\\" in text or "D:\\Learn" in text or "D:/Learn" in text:
                errors.append(f"Machine-specific path: {path.relative_to(root)}")
            for target in local_targets(path):
                counts["local_links"] += 1
                if not target.is_relative_to(root) or not target.is_file():
                    errors.append(f"Broken/outside reference in {path.relative_to(root)}: {target}")
        a = root / "skills/professor/references/host-adapters.md"
        b = root / "skills/course-tutor/references/host-adapters.md"
        if a.read_bytes() != b.read_bytes():
            errors.append("Host adapter copies have diverged")
        questions = []
        for path in (root / "skills/professor/references/questions").glob("*.md"):
            questions.extend(re.findall(r"\| (Q\d{3}) ·", path.read_text(encoding="utf-8")))
        counts["candidate_questions"] = len(questions)
        if set(questions) != {f"Q{i:03}" for i in range(1, 101)} or len(questions) != 100:
            errors.append("Question IDs missing or duplicated; this checks indexing, not interview quality")
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, **counts, "errors": errors,
            "scope": "Package layout, metadata and local references only; not native installation or teaching quality"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--schema", type=Path, help="Optional locally downloaded plugin JSON schema")
    args = p.parse_args()
    result = validate(args.root, args.schema)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
