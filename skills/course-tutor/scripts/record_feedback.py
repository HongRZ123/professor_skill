#!/usr/bin/env python3
"""Append a version-linked tutor report without changing professor-owned state."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path, PureWindowsPath
import re
import sys
import uuid


def inside(root, value):
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError("Use a forward-slash relative path")
    p = Path(value)
    if ":" in value or p.is_absolute() or PureWindowsPath(value).drive or ".." in p.parts:
        raise ValueError("Path must be workspace-relative")
    path = (root / p).resolve()
    if path == root or not path.is_relative_to(root):
        raise ValueError("Path escapes workspace")
    return path


def record(root, payload):
    state = json.loads(inside(root, "state.json").read_text(encoding="utf-8"))
    if state.get("workspace_format") != "professor-workspace-v1" or state.get("schema_version") != "1":
        raise ValueError("Not a supported professor workspace")
    required = ("lesson_id", "lesson_version", "material_location", "user_question", "response_summary", "evidence_kind")
    if not isinstance(payload, dict) or any(not isinstance(payload.get(k), str) or not payload[k].strip() for k in required):
        raise ValueError("Feedback requires lesson/version/location/question/response/evidence_kind")
    if payload["evidence_kind"] not in {"self_report", "observed_response", "unverified", "explanation_only"}:
        raise ValueError("Invalid evidence_kind; do not convert teaching into mastery")
    pubs = state.get("published_lessons", [])
    for key in ("lesson_id", "lesson_version"):
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", payload[key]):
            raise ValueError("Invalid lesson identity or version")
    match = next((x for x in pubs if x["lesson_id"] == payload["lesson_id"] and x["version"] == payload["lesson_version"]), None)
    if match is None:
        base = "lessons/" + payload["lesson_id"] + "/" + payload["lesson_version"]
        archived = inside(root, "history/" + base + "/" + base + "/lesson.meta.json")
        if not archived.is_file():
            raise ValueError("Feedback must name a current or archived published lesson version")
        meta = json.loads(archived.read_text(encoding="utf-8"))
        if meta.get("lesson_id") != payload["lesson_id"] or meta.get("version") != payload["lesson_version"] or meta.get("status") != "complete":
            raise ValueError("Archived publication identity mismatch")
        match = {"meta_path": base + "/lesson.meta.json"}
    if not inside(root, match["meta_path"]).is_file():
        raise ValueError("Published lesson metadata is missing")
    feedback_id = "F-" + uuid.uuid4().hex
    stamp = datetime.now(timezone.utc).isoformat()
    header = {"feedback_id": feedback_id, "course_id": state["course_id"], "lesson_id": payload["lesson_id"],
              "lesson_version": payload["lesson_version"], "evidence_kind": payload["evidence_kind"], "created_at": stamp}
    # JSON lines between YAML delimiters are valid YAML and preserve exact Unicode safely.
    text = "---\n" + "\n".join(k + ": " + json.dumps(v, ensure_ascii=False) for k, v in header.items()) + "\n---\n\n"
    for heading, key in [("材料位置", "material_location"), ("用户实际问题", "user_question"),
                         ("本次解释", "response_summary"), ("实际表现或自报", "learner_evidence"),
                         ("未解决事项", "unresolved"), ("给教授的建议", "recommendation")]:
        value = payload.get(key, "未提供；不推断。")
        if not isinstance(value, str):
            raise ValueError(f"{key} must be text")
        text += "## " + heading + "\n\n" + value + "\n\n"
    directory = inside(root, "handoff/from-tutor")
    directory.mkdir(parents=True, exist_ok=True)
    path = inside(root, "handoff/from-tutor/" + feedback_id + ".md")
    with path.open("x", encoding="utf-8", newline="\n") as f:
        f.write(text)
    return {"feedback_id": feedback_id, "path": path.relative_to(root).as_posix(),
            "professor_state_changed": False, "evidence_warning": "Caller must supply actual interaction; this script cannot prove it occurred"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--input", required=True, help="JSON report relative to workspace")
    a = p.parse_args()
    try:
        root = Path(a.root).expanduser().resolve()
        payload = json.loads(inside(root, a.input).read_text(encoding="utf-8"))
        print(json.dumps(record(root, payload), ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
