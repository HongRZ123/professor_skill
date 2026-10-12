#!/usr/bin/env python3
"""Local workspace files, not an autonomous teacher. Python 3.10+, standard library."""
import argparse
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import sys
import tempfile
import uuid

FORMAT = "professor-workspace-v1"
STAGES = {"awaiting_topic", "interviewing", "awaiting_brief_confirmation", "researching",
          "awaiting_syllabus_confirmation", "ready", "authoring_lesson", "awaiting_learner", "completed"}
EDITABLE = {"title", "stage", "brief", "syllabus", "active_lesson_id", "waiting_for",
            "checkpoint_ref", "return_to", "action_ref", "storage_mode"}
BEGIN, END = "<!-- professor:status:start -->", "<!-- professor:status:end -->"
GUIDANCE_MARKER = "<!-- professor:workspace-v1 -->"


class WorkspaceError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def contained(root, relative):
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise WorkspaceError("Use a nonempty forward-slash relative path")
    value = relative.split("#", 1)[0]
    p = Path(value)
    if not value or ":" in value or p.is_absolute() or PureWindowsPath(value).drive or ".." in p.parts:
        raise WorkspaceError(f"Path is not workspace-relative: {relative}")
    result = (root / p).resolve()
    if result == root or not result.is_relative_to(root):
        raise WorkspaceError(f"Path escapes workspace: {relative}")
    return result


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise WorkspaceError(f"Cannot read JSON {path}: {exc}") from exc


def require_file(root, ref):
    p = contained(root, ref)
    if not p.is_file() or not p.stat().st_size:
        raise WorkspaceError(f"Missing or empty file: {ref}")
    return p


def atomic_write(root, relative, data):
    path = contained(root, relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    # Resolve again after creating parents, including Windows junctions.
    path = contained(root, relative)
    fd, temp = tempfile.mkstemp(prefix=".professor-write-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


@contextmanager
def locked(root):
    lock = contained(root, ".professor-write.lock")
    token = str(uuid.uuid4())
    try:
        with lock.open("x", encoding="utf-8") as f:
            json.dump({"pid": os.getpid(), "token": token, "created_at": now()}, f)
    except FileExistsError as exc:
        raise WorkspaceError("Workspace is locked. Inspect .professor-write.lock; never remove a live writer's lock.") from exc
    try:
        yield
    finally:
        try:
            if read_json(lock).get("token") == token:
                lock.unlink()
        except (WorkspaceError, OSError):
            pass


def validate_state(s):
    if not isinstance(s, dict) or s.get("workspace_format") != FORMAT or s.get("schema_version") != "1":
        raise WorkspaceError("Unknown workspace/schema; do not reset or migrate automatically")
    if s.get("stage") not in STAGES or type(s.get("revision")) is not int or s["revision"] < 0:
        raise WorkspaceError("Invalid stage/revision")
    if not isinstance(s.get("course_id"), str) or not s["course_id"]:
        raise WorkspaceError("Missing course identity")
    if not isinstance(s.get("published_lessons"), list):
        raise WorkspaceError("published_lessons must be a list")
    if not isinstance(s.get("title"), str) or s.get("storage_mode") not in {"persistent", "session"}:
        raise WorkspaceError("Invalid title/storage_mode")
    for key in ("brief", "syllabus"):
        ref = s.get(key)
        if ref is not None and (not isinstance(ref, dict) or not ref.get("path") or not ref.get("version")):
            raise WorkspaceError(f"Invalid {key} reference")
    return s


def load_state(root):
    return validate_state(read_json(contained(root, "state.json")))


def expect_revision(s, expected):
    if s["revision"] != expected:
        raise WorkspaceError(f"Revision conflict: expected {expected}, actual {s['revision']}; reread before merging")


def status_block(s):
    title = s["title"].replace("\n", " ").replace("\r", " ")
    rows = [BEGIN, "## 当前课程", f"主题：{title or '等待学习对象'}", f"阶段：{s['stage']}",
            f"课程标识：{s['course_id']}", f"状态修订：{s['revision']}", "", '<a id="next-step"></a>',
            "## 接续", s.get("waiting_for") or "依据当前请求继续。", "", "## 已发布材料"]
    for item in s["published_lessons"]:
        rows.append(f"- [{item['lesson_id']} · {item['version']}]({item['lesson_path']})")
    if not s["published_lessons"]:
        rows.append("尚无正式课次。")
    rows.extend(["", "发布不代表已读或掌握；学习证据另见 learning 中的实际记录。", END])
    return "\n".join(rows)


def course_text(existing, s):
    if BEGIN not in existing and END not in existing:
        return existing.rstrip() + "\n\n" + status_block(s) + "\n"
    if existing.count(BEGIN) != 1 or existing.count(END) != 1 or existing.index(BEGIN) > existing.index(END):
        raise WorkspaceError("COURSE.md managed section is malformed; preserve and repair it explicitly")
    a, b = existing.index(BEGIN), existing.index(END) + len(END)
    return existing[:a] + status_block(s) + existing[b:]


def refresh(root, s):
    p = require_file(root, "COURSE.md")
    atomic_write(root, "COURSE.md", course_text(p.read_text(encoding="utf-8"), s).encode("utf-8"))


def init_workspace(root, topic="", storage_mode="persistent"):
    root.mkdir(parents=True, exist_ok=True)
    with locked(root):
        journal = contained(root, ".professor-init.json")
        state_file = contained(root, "state.json")
        if state_file.exists() and not journal.exists():
            s = load_state(root)
            require_file(root, "AGENTS.md")
            require_file(root, "COURSE.md")
            return {"created": False, "root": str(root), "state": s}
        if journal.exists():
            plan = read_json(journal)
            if plan.get("kind") != "professor-initialization-v1" or not isinstance(plan.get("files"), dict):
                raise WorkspaceError("Unrecognized initialization journal; preserve it")
        else:
            if state_file.exists() or contained(root, "COURSE.md").exists():
                raise WorkspaceError("Conflicting existing state.json/COURSE.md; choose a different root")
            if topic and contained(root, "intake/notes.md").exists():
                raise WorkspaceError("Existing intake/notes.md; inspect it rather than overwriting")
            s = {"schema_version": "1", "workspace_format": FORMAT, "course_id": str(uuid.uuid4()),
                 "revision": 0, "title": topic, "storage_mode": storage_mode,
                 "stage": "interviewing" if topic else "awaiting_topic", "brief": None,
                 "syllabus": None, "active_lesson_id": None, "published_lessons": [],
                 "waiting_for": "继续访谈，确认目标与相关基础。" if topic else "请提供学习主题、问题或教材。",
                 "checkpoint_ref": "COURSE.md#next-step", "updated_at": now()}
            guidance = (Path(__file__).resolve().parent.parent / "assets/workspace-guidance.md").read_text(encoding="utf-8")
            agents = contained(root, "AGENTS.md")
            original = agents.read_text(encoding="utf-8") if agents.exists() else ""
            if GUIDANCE_MARKER in original:
                raise WorkspaceError("Existing professor guidance without state; inspect partial or old workspace")
            files = {"AGENTS.md": original.rstrip() + ("\n\n" if original else "") + guidance,
                     "COURSE.md": "# 学习工作区\n\n课程入口；下方标记区由状态工具维护，用户说明可写在标记区之外。\n\n" + status_block(s) + "\n"}
            if topic:
                files["intake/notes.md"] = "# 访谈记录\n\n用户提出的学习对象：" + topic + "\n\n目标、基础与范围尚待访谈，不视为已确认。\n"
            files["state.json"] = json_bytes(s).decode("utf-8")
            plan = {"kind": "professor-initialization-v1", "files": files,
                    "previous_agents": original if agents.exists() else None}
            atomic_write(root, ".professor-init.json", json_bytes(plan))
        for relative, content in plan["files"].items():
            if relative not in {"AGENTS.md", "COURSE.md", "intake/notes.md", "state.json"} or not isinstance(content, str):
                raise WorkspaceError("Invalid file in initialization journal")
            path = contained(root, relative)
            if path.exists():
                current = path.read_text(encoding="utf-8")
                if current == content:
                    continue
                if relative != "AGENTS.md" or current != plan.get("previous_agents"):
                    raise WorkspaceError(f"Partial initialization conflicts with {relative}; preserve both")
            atomic_write(root, relative, content.encode("utf-8"))
        s = load_state(root)
        journal.unlink()
        return {"created": True, "root": str(root), "state": s}


def reference_ok(root, value, confirmed=False):
    if not isinstance(value, dict) or not value.get("version"):
        raise WorkspaceError("Document reference needs a version")
    require_file(root, value.get("path"))
    if confirmed:
        require_file(root, value.get("confirmation_ref"))


def stage_requirements(root, s):
    stage = s["stage"]
    for key in ("brief", "syllabus"):
        if s.get(key):
            reference_ok(root, s[key])
            if s[key].get("confirmation_ref"):
                require_file(root, s[key]["confirmation_ref"])
    if stage == "awaiting_brief_confirmation":
        reference_ok(root, s.get("brief"))
    if stage in {"researching", "awaiting_syllabus_confirmation", "ready", "authoring_lesson", "awaiting_learner"}:
        reference_ok(root, s.get("brief"), confirmed=True)
    if stage == "awaiting_syllabus_confirmation":
        reference_ok(root, s.get("syllabus"))
        for ref in ("research/report.md", "research/knowledge-structure.md", "research/sources.json"):
            require_file(root, ref)
    if stage in {"ready", "authoring_lesson", "awaiting_learner"}:
        reference_ok(root, s.get("syllabus"), confirmed=True)
    if stage == "authoring_lesson":
        valid_id(s.get("active_lesson_id"), "lesson id")
        require_file(root, s.get("action_ref"))
    if s.get("checkpoint_ref"):
        require_file(root, s["checkpoint_ref"])
    if s.get("return_to") is not None and s["return_to"] not in STAGES:
        raise WorkspaceError("Invalid return_to stage")


def update_state(root, expected, patch):
    if not isinstance(patch, dict) or set(patch) - EDITABLE:
        raise WorkspaceError("Patch has unknown/read-only fields; publishing has a separate command")
    with locked(root):
        old = load_state(root)
        expect_revision(old, expected)
        s = {**deepcopy(old), **patch, "revision": old["revision"] + 1, "updated_at": now()}
        validate_state(s)
        stage_requirements(root, s)
        if s["stage"] in {"ready", "authoring_lesson"}:
            materials = check_materials(root, s.get("active_lesson_id") if s["stage"] == "authoring_lesson" else None)
            if not materials["ok"]:
                raise WorkspaceError("Course materials are not ready: " + "; ".join(materials["errors"]))
        if s["stage"] == "awaiting_learner" and not s["published_lessons"]:
            raise WorkspaceError("Cannot claim a lesson was published without a publication record")
        if s["stage"] == "completed" and old["stage"] != "completed":
            require_file(root, s.get("action_ref"))
        # Validate navigation before committing authoritative state.
        course_text(require_file(root, "COURSE.md").read_text(encoding="utf-8"), s)
        atomic_write(root, "state.json", json_bytes(s))
        refresh(root, s)
        return s


def valid_id(value, label):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", value):
        raise WorkspaceError(f"Invalid {label}")
    return value


def prose_units(text):
    """Approximate main-body amount, never an estimate of understanding or elapsed time."""
    text = re.sub(r"```.*?```|~~~.*?~~~", "", text, flags=re.S)
    text = "\n".join(line for line in text.splitlines() if not re.match(r"^\s*(?:#{1,6}\s|\||>)", line))
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"<[^>]+>|https?://\S+", "", text)
    return len(re.findall(r"[\u3400-\u4dbf\u4e00-\u9fff]", text)) + len(re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*", text))


def check_materials(root, lesson_id=None):
    errors, refs, selected, entries = [], [], None, {}
    for ref in ("materials/index.md", "materials/reading-plan.md", "materials/catalog.json"):
        try:
            require_file(root, ref)
            refs.append(ref)
        except WorkspaceError as exc:
            errors.append(str(exc))
    try:
        catalog = read_json(require_file(root, "materials/catalog.json"))
        sources = read_json(require_file(root, "research/sources.json"))
        source_ids = {x["source_id"] for x in sources}
        if not isinstance(catalog, dict) or not isinstance(catalog.get("materials"), list) or not catalog["materials"]:
            raise WorkspaceError("Material catalog needs actual materials")
        for item in catalog["materials"]:
            sid = valid_id(item.get("source_id"), "material source id")
            if sid in entries or sid not in source_ids:
                raise WorkspaceError("Duplicate or unregistered material source: " + sid)
            entries[sid] = item
            if item.get("role") not in {"core", "support", "further"}:
                raise WorkspaceError("Material needs a core/support/further role: " + sid)
            if not all(isinstance(item.get(k), str) and item[k].strip() for k in ("edition", "access_note")):
                raise WorkspaceError("Material needs actual edition and access note: " + sid)
            available = item.get("availability")
            if available == "local":
                require_file(root, item.get("local_path"))
            elif available == "online":
                from urllib.parse import urlparse
                url = urlparse(item.get("url", ""))
                if url.scheme not in {"http", "https"} or not url.netloc:
                    raise WorkspaceError("Online material needs an actual URL: " + sid)
            elif available == "user-copy":
                require_file(root, item.get("confirmation_ref"))
            elif available != "unavailable":
                raise WorkspaceError("Unknown material availability: " + sid)
            if item["role"] == "core" and available == "unavailable":
                errors.append("Core material unavailable: " + sid)
        if not any(x["role"] == "core" for x in entries.values()):
            errors.append("No selected core textbook or core source set")
        lessons = catalog.get("lessons")
        if not isinstance(lessons, list) or not lessons:
            raise WorkspaceError("Material catalog needs per-lesson reading assignments")
        seen = set()
        for lesson in lessons:
            lid = valid_id(lesson.get("lesson_id"), "reading lesson id")
            if lid in seen:
                raise WorkspaceError("Duplicate lesson reading map: " + lid)
            seen.add(lid)
            if lid == lesson_id:
                selected = lesson
            for phase in ("before", "in_class", "after"):
                tasks = lesson.get(phase)
                if not isinstance(tasks, list) or (phase != "before" and not tasks):
                    raise WorkspaceError(f"{lid} needs explicit {phase} reading assignments")
                if phase == "before" and not tasks and not lesson.get("before_note"):
                    raise WorkspaceError("Explain why no pre-reading is assigned: " + lid)
                for task in tasks:
                    if task.get("source_id") not in entries or not all(isinstance(task.get(k), str) and task[k].strip() for k in ("locator", "purpose")):
                        raise WorkspaceError(f"{lid}/{phase}: reading needs registered source, exact locator and purpose")
                    if lid == lesson_id and entries[task["source_id"]]["availability"] == "unavailable":
                        errors.append(f"Current lesson reading unavailable: {lid}/{task['source_id']}")
        if lesson_id and selected is None:
            errors.append("No reading map for current lesson: " + lesson_id)
    except (WorkspaceError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, "errors": errors, "refs": refs, "lesson_readings": selected, "materials": entries}


def check_delivery(root, lesson_id, meta=None):
    materials = check_materials(root, lesson_id)
    errors, warnings = list(materials["errors"]), []
    metrics = {"prose_units": 0, "minimum_prose_units": 24000, "embedded_visuals": 0}
    try:
        valid_id(lesson_id, "lesson id")
        if meta is None:
            meta = read_json(require_file(root, f"lessons/{lesson_id}/lesson.meta.json"))
        body = require_file(root, meta.get("lesson_path"))
        text = body.read_text(encoding="utf-8")
        metrics["prose_units"] = prose_units(text)
        delivery = meta.get("delivery") or {}
        if delivery.get("standard") != "lecture-120-v1":
            errors.append("Missing lecture-120-v1 delivery contract; do not mark a short draft as a complete class")
        minimum, minutes = 24000, 120
        override = delivery.get("override")
        if override is not None:
            require_file(root, override.get("confirmation_ref"))
            if not override.get("reason") or any(type(override.get(k)) is not int or override[k] <= 0 for k in ("lecture_minutes", "min_prose_units")):
                raise WorkspaceError("Explicit user format override needs reason and positive minutes/prose minimum")
            minimum, minutes = override["min_prose_units"], override["lecture_minutes"]
            warnings.append("Nonstandard format declared: verify actual user authorization; file existence is not consent")
        metrics["minimum_prose_units"] = minimum
        if delivery.get("lecture_minutes") != minutes:
            errors.append(f"Lesson must declare {minutes} lecture minutes; weekly budget is not a per-class override")
        if metrics["prose_units"] < minimum:
            errors.append(f"Lecture body too short: {metrics['prose_units']} prose units; minimum {minimum}. Continue expanding this draft.")
        readings = materials["lesson_readings"] or {}
        in_class = {x["source_id"] for x in readings.get("in_class", [])}
        callbacks = delivery.get("callbacks")
        if not isinstance(callbacks, list) or not callbacks:
            errors.append("Missing substantive textbook callbacks linked to the reading map")
        else:
            matched = set()
            for item in callbacks:
                if not isinstance(item, dict) or item.get("source_id") not in in_class or item.get("source_id") not in meta.get("source_ids", []):
                    errors.append("Textbook callback must name a read source in this lesson's in-class reading map")
                    continue
                location = item.get("lesson_location")
                if not item.get("locator") or not isinstance(location, str) or not location.strip() or location not in text:
                    errors.append("Callback needs an actual source locator and an existing lesson location")
                    continue
                matched.add(item["source_id"])
            if not matched:
                errors.append("No verifiable callback location in the lecture body")
        from urllib.parse import unquote
        image_targets = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
        link_targets = re.findall(r"\[[^\]]*\]\(([^)]+)\)", text)
        def linked(targets, path):
            return any((body.parent / unquote(t.strip('<>').split('#', 1)[0])).resolve() == path for t in targets if not re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", t))
        for asset in meta.get("assets", []):
            if asset.get("kind") not in {"generated-image", "source-image", "data-chart", "diagram", "interactive"}:
                continue
            path = require_file(root, asset.get("path"))
            embedded = linked(image_targets, path) or (path.suffix.lower() == ".html" and linked(link_targets, path))
            anchor = asset.get("embedded_anchor")
            if anchor:
                marker = re.search(r'<a\s+id=["\']' + re.escape(anchor) + r'["\']\s*>\s*</a>', text)
                following = text[marker.end():] if marker else ""
                block = re.match(r"\s*```mermaid\s*\n(.*?)```", following, re.S)
                embedded = bool(block and block.group(1).strip() == path.read_text(encoding="utf-8").strip())
            if embedded:
                metrics["embedded_visuals"] += 1
            else:
                errors.append("Visual asset is not embedded in the lesson: " + asset["path"])
        if metrics["embedded_visuals"] == 0:
            exception = delivery.get("visual_exception")
            if exception and exception.get("reason") and exception.get("fallback"):
                require_file(root, exception.get("evidence_ref"))
                warnings.append("Visual exception declared: inspect evidence; wording alone cannot prove tools were unavailable or user opted out")
            else:
                errors.append("No embedded teaching visuals; create and explain them, or record a genuine capability/user exception")
        elif metrics["embedded_visuals"] == 1:
            warnings.append("Only one embedded visual: this does not establish rich visual teaching; review distributed visual explanations")
    except (WorkspaceError, OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, "errors": errors, "warnings": warnings, "metrics": metrics,
            "scope": "Delivery omissions and file facts only, not teaching depth, source truth, consent or actual class duration"}


def check_lesson(root, s, lesson_id, allow_draft=False):
    valid_id(lesson_id, "lesson id")
    meta_path = f"lessons/{lesson_id}/lesson.meta.json"
    meta = read_json(require_file(root, meta_path))
    if not isinstance(meta, dict) or meta.get("lesson_id") != lesson_id:
        raise WorkspaceError("Lesson identity mismatch")
    valid_id(meta.get("version"), "lesson version")
    if meta.get("status") not in ({"draft", "complete"} if allow_draft else {"complete"}):
        raise WorkspaceError("Lesson is not complete")
    if meta.get("syllabus_version") != (s.get("syllabus") or {}).get("version"):
        raise WorkspaceError("Lesson uses a different syllabus version; reconcile explicitly")
    body = require_file(root, meta.get("lesson_path"))
    if not body.is_relative_to(contained(root, f"lessons/{lesson_id}/{meta['version']}")):
        raise WorkspaceError("Lesson body must be inside its version directory: lessons/ID/VERSION/")
    version_root = contained(root, f"lessons/{lesson_id}/{meta['version']}")
    review = require_file(root, meta.get("review_ref"))
    if not review.is_relative_to(version_root):
        raise WorkspaceError("Review must be inside the lesson version directory")
    registry = read_json(require_file(root, "research/sources.json"))
    if not isinstance(registry, list):
        raise WorkspaceError("sources.json must be an array")
    indexed = {}
    for source in registry:
        if not isinstance(source, dict):
            raise WorkspaceError("Invalid source entry")
        sid = valid_id(source.get("source_id"), "source id")
        if sid in indexed:
            raise WorkspaceError("Duplicate source id: " + sid)
        indexed[sid] = source
    ids = meta.get("source_ids")
    if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
        raise WorkspaceError("Lesson needs distinct source_ids")
    for sid in ids:
        source = indexed.get(sid, {})
        if not all(isinstance(source.get(k), str) and source[k].strip() for k in ("title", "origin", "read_scope", "access")):
            raise WorkspaceError(f"Source {sid} missing identity/access/actual reading scope")
        if source["access"] not in {"full", "excerpt", "abstract"}:
            raise WorkspaceError(f"Source {sid} needs an actual full/excerpt/abstract access record")
        if source.get("local_path"):
            require_file(root, source["local_path"])
    assets = meta.get("assets", [])
    if not isinstance(assets, list):
        raise WorkspaceError("assets must be an array")
    refs = [meta["lesson_path"], meta["review_ref"], "research/sources.json"]
    for asset in assets:
        if not isinstance(asset, dict) or asset.get("kind") not in {"generated-image", "source-image", "data-chart", "diagram", "interactive", "other"}:
            raise WorkspaceError("Asset kind must describe its provenance")
        for key in ("path", "purpose", "provenance", "checked"):
            if not asset.get(key):
                raise WorkspaceError(f"Asset needs {key}")
        if asset["checked"] is not True:
            raise WorkspaceError("Asset must be marked checked after actual inspection")
        for key in ("path", "data_path", "script_path", "fallback_path"):
            if asset.get(key):
                asset_file = require_file(root, asset[key])
                if not asset_file.is_relative_to(version_root):
                    raise WorkspaceError("Published assets and their dependencies must be inside the lesson version directory")
                refs.append(asset[key])
        if asset["kind"] == "data-chart" and not all(asset.get(k) for k in ("data_path", "script_path")):
            raise WorkspaceError("Data charts need data_path and script_path")
        if asset["kind"] == "interactive" and not asset.get("fallback_path"):
            raise WorkspaceError("Interactive material needs a usable fallback file")
    # Check local Markdown targets. Remote content, fragments and semantic support are not validated.
    for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", body.read_text(encoding="utf-8")):
        target = target.strip("<>").split("#", 1)[0]
        if not target or re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", target):
            continue
        from urllib.parse import unquote
        actual = (body.parent / unquote(target)).resolve()
        if not actual.is_relative_to(root) or not actual.is_file():
            raise WorkspaceError(f"Broken/outside lesson link: {target}")
        refs.append(actual.relative_to(root).as_posix())
    delivery = check_delivery(root, lesson_id, meta)
    if not delivery["ok"]:
        raise WorkspaceError("Lecture delivery incomplete: " + "; ".join(delivery["errors"]))
    refs.extend(["materials/index.md", "materials/reading-plan.md", "materials/catalog.json"])
    return meta, sorted(set(refs))


def publish(root, expected, lesson_id):
    with locked(root):
        s = load_state(root)
        expect_revision(s, expected)
        if s["stage"] != "authoring_lesson" or s.get("active_lesson_id") != lesson_id:
            raise WorkspaceError("Start this lesson explicitly before publishing")
        stage_requirements(root, s)
        course_text(require_file(root, "COURSE.md").read_text(encoding="utf-8"), s)
        meta, refs = check_lesson(root, s, lesson_id, allow_draft=True)
        meta["status"] = "complete"
        meta_path = f"lessons/{lesson_id}/{meta['version']}/lesson.meta.json"
        content = {ref: require_file(root, ref).read_bytes() for ref in refs}
        content[meta_path] = json_bytes(meta)
        archive = f"history/lessons/{lesson_id}/{meta['version']}"
        for ref, data in content.items():
            dest = contained(root, archive + "/" + ref)
            if dest.exists() and dest.read_bytes() != data:
                raise WorkspaceError("Published version already exists with different contents; use a new version")
        for ref, data in content.items():
            dest = contained(root, archive + "/" + ref)
            if not dest.exists():
                atomic_write(root, archive + "/" + ref, data)
        archive_hashes = {ref: hashlib.sha256(data).hexdigest() for ref, data in content.items()}
        # The registry and navigation may evolve. Preserve their publication-time
        # snapshots, but only freeze live files belonging to this lesson version.
        prefix = f"lessons/{lesson_id}/{meta['version']}/"
        hashes = {ref: digest for ref, digest in archive_hashes.items() if ref.startswith(prefix)}
        atomic_write(root, meta_path, json_bytes(meta))
        atomic_write(root, f"lessons/{lesson_id}/lesson.meta.json", json_bytes(meta))
        entry = {"lesson_id": lesson_id, "version": meta["version"], "lesson_path": meta["lesson_path"],
                 "meta_path": meta_path, "archive_path": archive, "hashes": hashes,
                 "archive_hashes": archive_hashes, "published_at": now()}
        s["published_lessons"] = [x for x in s["published_lessons"] if x["lesson_id"] != lesson_id] + [entry]
        s.update(stage="awaiting_learner", waiting_for="本课材料已保存，可阅读、提问或请求下一课；理解程度待实际反馈。",
                 revision=s["revision"] + 1, updated_at=now())
        atomic_write(root, "state.json", json_bytes(s))
        refresh(root, s)
        return entry


def check_workspace(root):
    errors, warnings = [], []
    try:
        s = load_state(root)
        for path in ("AGENTS.md", "COURSE.md"):
            require_file(root, path)
        stage_requirements(root, s)
        if status_block(s) not in (root / "COURSE.md").read_text(encoding="utf-8"):
            warnings.append("COURSE.md navigation is stale; run refresh after inspecting state")
        if contained(root, ".professor-init.json").exists():
            warnings.append("Initialization journal remains; rerun init to reconcile, do not reset")
        for entry in s["published_lessons"]:
            for ref, digest in entry.get("archive_hashes", {}).items():
                p = require_file(root, entry["archive_path"] + "/" + ref)
                if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                    errors.append(f"Publication snapshot changed: {ref}")
            for ref, digest in entry.get("hashes", {}).items():
                p = require_file(root, ref)
                if hashlib.sha256(p.read_bytes()).hexdigest() != digest:
                    errors.append(f"Published file changed without a new publication: {ref}")
        for p in root.glob("lessons/*/lesson.meta.json"):
            if not p.resolve().is_relative_to(root):
                errors.append("Outside lesson metadata symlink")
                continue
            meta = read_json(p)
            if meta.get("status") == "complete" and not any(x["lesson_id"] == meta.get("lesson_id") and x["version"] == meta.get("version") for x in s["published_lessons"]):
                warnings.append(f"Complete metadata without matching publication pointer: {p.relative_to(root)}")
    except (WorkspaceError, OSError, KeyError, TypeError, ValueError) as exc:
        errors.append(str(exc))
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "scope": "Local files, versions and hashes only; not user consent, source truth, teaching depth or mastery"}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("command", choices=["init", "status", "update", "publish", "check", "refresh"])
    p.add_argument("--root", required=True)
    p.add_argument("--topic", default="")
    p.add_argument("--storage-mode", choices=["persistent", "session"], default="persistent")
    p.add_argument("--expected-revision", type=int)
    p.add_argument("--patch", help="JSON patch path relative to course root")
    p.add_argument("--lesson")
    args = p.parse_args()
    root = Path(args.root).expanduser().resolve()
    try:
        if args.command == "init":
            result = init_workspace(root, args.topic, args.storage_mode)
        elif args.command == "status":
            result = {"root": str(root), "state": load_state(root), "check": check_workspace(root)}
        elif args.command == "check":
            result = check_workspace(root)
        else:
            if args.expected_revision is None:
                raise WorkspaceError("--expected-revision is required for mutations")
            if args.command == "update":
                result = update_state(root, args.expected_revision, read_json(require_file(root, args.patch)))
            elif args.command == "publish":
                result = publish(root, args.expected_revision, args.lesson)
            else:
                with locked(root):
                    result = load_state(root)
                    expect_revision(result, args.expected_revision)
                    refresh(root, result)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if isinstance(result, dict) and result.get("ok") is False else 0
    except (WorkspaceError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
