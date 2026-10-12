"""Synthetic file lifecycle tests. These do not simulate learning or user consent."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

LIBRARY = Path(__file__).resolve().parents[1]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


cs = module("course_state", LIBRARY / "skills/professor/scripts/course_state.py")
rf = module("record_feedback", LIBRARY / "skills/course-tutor/scripts/record_feedback.py")


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        test_root = (LIBRARY / "build/test-workspaces").resolve()
        test_root.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=test_root)
        # Confirm recursive cleanup is confined to our dedicated test area.
        assert Path(self.temp.name).resolve().is_relative_to(test_root)
        self.addCleanup(self.temp.cleanup)
        self.root = (Path(self.temp.name) / "课程").resolve()
        self.root.mkdir()

    def put(self, path, value):
        data = cs.json_bytes(value) if isinstance(value, (dict, list)) else value.encode("utf-8")
        cs.atomic_write(self.root, path, data)

    def update(self, **changes):
        return cs.update_state(self.root, cs.load_state(self.root)["revision"], changes)

    def ready(self):
        cs.init_workspace(self.root, "合成协议测试，非真实学习")
        self.put("intake/brief.md", "Synthetic brief")
        self.put("intake/decisions.md", "Synthetic confirmations for automated file tests only")
        brief = {"path": "intake/brief.md", "version": "b1"}
        self.update(stage="awaiting_brief_confirmation", brief=brief)
        brief["confirmation_ref"] = "intake/decisions.md"
        self.update(stage="researching", brief=brief)
        self.put("research/report.md", "Synthetic report")
        self.put("research/knowledge-structure.md", "Synthetic structure")
        self.put("research/sources.json", [{"source_id": "S001", "title": "Synthetic source",
            "origin": "test fixture", "version": "test-1", "access": "full",
            "read_scope": "Synthetic data, not a real reading claim", "role": "test"}])
        self.put("syllabus/syllabus.md", "Synthetic syllabus")
        syllabus = {"path": "syllabus/syllabus.md", "version": "s1"}
        self.update(stage="awaiting_syllabus_confirmation", syllabus=syllabus)
        syllabus["confirmation_ref"] = "intake/decisions.md"
        self.put("materials/index.md", "Synthetic materials index")
        self.put("materials/reading-plan.md", "Synthetic course reading map")
        self.put("materials/files/core.txt", "Synthetic core source, not a real textbook")
        self.put("materials/catalog.json", {"materials": [
            {"source_id": "S001", "role": "core", "edition": "synthetic version", "availability": "local",
             "local_path": "materials/files/core.txt", "access_note": "Test fixture only"}],
            "lessons": [{"lesson_id": "L01", "before": [], "before_note": "No pre-reading for synthetic test",
                "in_class": [{"source_id": "S001", "locator": "fixture paragraph", "purpose": "protocol test"}],
                "after": [{"source_id": "S001", "locator": "fixture paragraph", "purpose": "test rereading"}]}]})
        self.update(stage="ready", syllabus=syllabus)

    def long_body(self):
        # Deliberately repetitive synthetic input tests the amount guard only.
        # It must never be presented as a real lecture or evidence of teaching depth.
        return "# Synthetic fixture\n\n" + "合成测试文本仅供长度与文件协议验证不代表教学效果。" * 1200 + "\n\n![Synthetic diagram](diagram.svg)\n[registry](../../../research/sources.json)\n"

    def draft(self, version="v1"):
        self.put("lesson-request.md", "Synthetic request for protocol test")
        self.update(stage="authoring_lesson", active_lesson_id="L01", action_ref="lesson-request.md")
        base = "lessons/L01/" + version
        self.put(base + "/lesson.md", self.long_body())
        self.put(base + "/review.md", "Synthetic review record, not teaching validation")
        self.put(base + "/diagram.svg", '<svg xmlns="http://www.w3.org/2000/svg"><text x="5" y="20">Test fixture</text></svg>')
        meta = {"lesson_id": "L01", "version": version, "syllabus_version": "s1", "status": "draft",
            "lesson_path": base + "/lesson.md", "review_ref": base + "/review.md", "source_ids": ["S001"],
            "assets": [{"kind": "diagram", "path": base + "/diagram.svg", "purpose": "synthetic test", "provenance": "synthetic", "checked": True}],
            "delivery": {"standard": "lecture-120-v1", "lecture_minutes": 120,
                "callbacks": [{"source_id": "S001", "locator": "fixture paragraph", "lesson_location": "Synthetic fixture"}]}}
        self.put("lessons/L01/lesson.meta.json", meta)
        return meta

    def publish(self):
        return cs.publish(self.root, cs.load_state(self.root)["revision"], "L01")

    def test_init_is_idempotent_and_preserves_agents(self):
        self.put("AGENTS.md", "User workspace instructions\n")
        first = cs.init_workspace(self.root, "康德")
        before = (self.root / "state.json").read_bytes()
        self.assertEqual(first["state"]["title"], "康德")
        self.assertTrue((self.root / "AGENTS.md").read_text(encoding="utf-8").startswith("User workspace instructions"))
        self.assertFalse(cs.init_workspace(self.root, "Other")["created"])
        self.assertEqual(before, (self.root / "state.json").read_bytes())

    def test_topicless_and_session_modes(self):
        s = cs.init_workspace(self.root, storage_mode="session")["state"]
        self.assertEqual(s["stage"], "awaiting_topic")
        self.assertEqual(s["storage_mode"], "session")
        self.assertFalse((self.root / "intake").exists())

    def test_conflicting_course_is_preserved(self):
        self.put("COURSE.md", "Existing course")
        with self.assertRaises(cs.WorkspaceError):
            cs.init_workspace(self.root, "New")
        self.assertEqual((self.root / "COURSE.md").read_text(), "Existing course")
        self.assertFalse((self.root / "state.json").exists())

    def interrupt_init(self):
        actual = cs.atomic_write
        def interrupt(root, relative, data):
            if relative == "COURSE.md":
                raise OSError("Synthetic interruption")
            actual(root, relative, data)
        with patch.object(cs, "atomic_write", side_effect=interrupt):
            with self.assertRaises(OSError):
                cs.init_workspace(self.root, "Interrupted")

    def test_partial_initialization_recovers(self):
        self.interrupt_init()
        self.assertTrue((self.root / ".professor-init.json").exists())
        result = cs.init_workspace(self.root)
        self.assertEqual(result["state"]["title"], "Interrupted")
        self.assertTrue(cs.check_workspace(self.root)["ok"])
        self.assertFalse((self.root / ".professor-init.json").exists())

    def test_partial_initialization_does_not_overwrite_changes(self):
        self.interrupt_init()
        self.put("AGENTS.md", "Changed after interruption")
        with self.assertRaises(cs.WorkspaceError):
            cs.init_workspace(self.root)
        self.assertEqual((self.root / "AGENTS.md").read_text(), "Changed after interruption")

    def test_path_escape_rejected(self):
        for bad in ("../escape", "/absolute", "C:/escape", "a/../../b", "a\\b", "file:stream", "."):
            with self.subTest(path=bad), self.assertRaises(cs.WorkspaceError):
                cs.contained(self.root, bad)
            with self.subTest(tutor_path=bad), self.assertRaises(ValueError):
                rf.inside(self.root, bad)

    def test_outside_symlink_rejected(self):
        outside = self.root.parent / "outside"
        outside.mkdir()
        try:
            (self.root / "linked").symlink_to(outside, target_is_directory=True)
        except OSError as exc:
            self.skipTest("Host does not permit directory symlinks: " + str(exc))
        with self.assertRaises(cs.WorkspaceError):
            cs.contained(self.root, "linked/file.md")

    def test_revision_conflict_and_identity_change_rejected(self):
        cs.init_workspace(self.root)
        self.update(title="Updated")
        with self.assertRaises(cs.WorkspaceError):
            cs.update_state(self.root, 0, {"title": "Stale"})
        with self.assertRaises(cs.WorkspaceError):
            self.update(course_id="Other identity")
        self.assertEqual(cs.load_state(self.root)["title"], "Updated")

    def test_missing_confirmations_cannot_advance(self):
        cs.init_workspace(self.root)
        for stage in ("researching", "ready", "authoring_lesson", "awaiting_learner", "completed"):
            with self.subTest(stage=stage), self.assertRaises(cs.WorkspaceError):
                self.update(stage=stage)
        self.assertEqual(cs.load_state(self.root)["revision"], 0)

    def test_full_lifecycle_source_updates_and_relocation(self):
        self.ready()
        self.draft()
        entry = self.publish()
        s = cs.load_state(self.root)
        self.assertEqual(s["stage"], "awaiting_learner")
        self.assertNotIn("mastery", s)
        self.assertTrue(cs.check_workspace(self.root)["ok"])
        registry = cs.read_json(self.root / "research/sources.json")
        registry.append({"source_id": "S002", "title": "Future research"})
        self.put("research/sources.json", registry)
        self.assertTrue(cs.check_workspace(self.root)["ok"])
        snapshot = self.root / entry["archive_path"] / "research/sources.json"
        self.assertEqual(len(cs.read_json(snapshot)), 1)
        moved = self.root.parent / "moved"
        shutil.copytree(self.root, moved)
        self.assertTrue(cs.check_workspace(moved.resolve())["ok"])

    def test_asset_failures_and_source_scope_are_rejected(self):
        self.ready()
        meta = self.draft()
        original_assets = meta["assets"]
        meta["assets"] = [{"kind": "diagram", "path": "lessons/L01/v1/missing.svg", "purpose": "test", "provenance": "test", "checked": True}]
        self.put("lessons/L01/lesson.meta.json", meta)
        with self.assertRaises(cs.WorkspaceError):
            self.publish()
        meta["assets"] = original_assets
        self.put("lessons/L01/lesson.meta.json", meta)
        sources = cs.read_json(self.root / "research/sources.json")
        for key, bad in (("read_scope", ""), ("access", "not_read"), ("access", "unknown"), ("source_id", "S999")):
            changed = [dict(sources[0], **{key: bad})]
            self.put("research/sources.json", changed)
            with self.subTest(key=key), self.assertRaises(cs.WorkspaceError):
                self.publish()

    def test_charts_require_reproducible_files(self):
        self.ready()
        meta = self.draft()
        self.put("lessons/L01/v1/chart.svg", "<svg/>")
        asset = {"kind": "data-chart", "path": "lessons/L01/v1/chart.svg", "purpose": "test", "provenance": "synthetic", "checked": True}
        meta["assets"] = [asset]
        self.put("lessons/L01/lesson.meta.json", meta)
        with self.assertRaises(cs.WorkspaceError):
            self.publish()
        self.put("lessons/L01/v1/data.csv", "a,b\n1,2\n")
        self.put("lessons/L01/v1/draw.py", "# synthetic fixture only\n")
        asset.update(data_path="lessons/L01/v1/data.csv", script_path="lessons/L01/v1/draw.py")
        self.put("lessons/L01/v1/lesson.md", self.long_body() + "\n![Chart](chart.svg)\n")
        self.put("lessons/L01/lesson.meta.json", meta)
        self.publish()
        self.assertTrue(cs.check_workspace(self.root)["ok"])

    def test_published_tampering_is_detected(self):
        self.ready()
        self.draft()
        self.publish()
        self.put("lessons/L01/v1/lesson.md", "Silently replaced")
        self.assertFalse(cs.check_workspace(self.root)["ok"])

    def test_interactive_requires_fallback_and_real_inspection(self):
        self.ready()
        meta = self.draft()
        self.put("lessons/L01/v1/view.html", "<html>Synthetic fixture</html>")
        asset = {"kind": "interactive", "path": "lessons/L01/v1/view.html", "purpose": "test", "provenance": "synthetic", "checked": False}
        meta["assets"] = [asset]
        self.put("lessons/L01/lesson.meta.json", meta)
        with self.assertRaises(cs.WorkspaceError):
            self.publish()
        asset["checked"] = True
        self.put("lessons/L01/lesson.meta.json", meta)
        with self.assertRaises(cs.WorkspaceError):
            self.publish()
        self.put("lessons/L01/v1/fallback.md", "Text fallback for synthetic test")
        asset["fallback_path"] = "lessons/L01/v1/fallback.md"
        self.put("lessons/L01/v1/lesson.md", self.long_body() + "\n[Interactive](view.html)\n")
        self.put("lessons/L01/lesson.meta.json", meta)
        self.publish()
        self.assertTrue(cs.check_workspace(self.root)["ok"])

    def test_broken_navigation_does_not_partially_publish(self):
        self.ready()
        self.draft()
        before = (self.root / "state.json").read_bytes()
        self.put("COURSE.md", "User notes\n" + cs.BEGIN)
        with self.assertRaises(cs.WorkspaceError):
            self.publish()
        self.assertEqual(before, (self.root / "state.json").read_bytes())
        self.assertFalse((self.root / "history/lessons/L01/v1").exists())

    def test_new_version_preserves_previous_version(self):
        self.ready()
        self.draft()
        self.publish()
        previous = (self.root / "lessons/L01/v1/lesson.md").read_bytes()
        self.draft("v2")
        self.put("lessons/L01/v2/lesson.md", self.long_body() + "\nRevised synthetic fixture\n")
        self.publish()
        self.assertEqual(previous, (self.root / "lessons/L01/v1/lesson.md").read_bytes())
        self.assertEqual(cs.load_state(self.root)["published_lessons"][0]["version"], "v2")
        self.assertTrue(cs.check_workspace(self.root)["ok"])

    def test_same_version_replacement_is_rejected(self):
        self.ready()
        self.draft()
        self.publish()
        self.update(stage="authoring_lesson")
        self.put("lessons/L01/v1/lesson.md", "Replacement")
        with self.assertRaises(cs.WorkspaceError):
            self.publish()

    def test_existing_lock_is_never_removed(self):
        cs.init_workspace(self.root)
        self.put(".professor-write.lock", {"token": "other-writer"})
        with self.assertRaises(cs.WorkspaceError):
            self.update(title="collision")
        self.assertEqual(cs.read_json(self.root / ".professor-write.lock")["token"], "other-writer")

    def test_tutor_report_preserves_state_and_rejects_wrong_version(self):
        self.ready()
        self.draft()
        self.publish()
        before = (self.root / "state.json").read_bytes()
        payload = {"lesson_id": "L01", "lesson_version": "v1", "material_location": "test paragraph",
            "user_question": "Synthetic question", "response_summary": "Synthetic explanation", "evidence_kind": "explanation_only"}
        a, b = rf.record(self.root, payload), rf.record(self.root, payload)
        self.assertNotEqual(a["path"], b["path"])
        self.assertTrue((self.root / a["path"]).is_file())
        self.assertEqual(before, (self.root / "state.json").read_bytes())
        payload["lesson_version"] = "v999"
        with self.assertRaises(ValueError):
            rf.record(self.root, payload)

    def test_cli_utf8_and_nonzero_conflict(self):
        script = LIBRARY / "skills/professor/scripts/course_state.py"
        cmd = [sys.executable, "-X", "utf8", str(script)]
        out = subprocess.run(cmd + ["init", "--root", str(self.root), "--topic", "康德"], capture_output=True, encoding="utf-8")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)["state"]["title"], "康德")
        out = subprocess.run(cmd + ["update", "--root", str(self.root)], capture_output=True, encoding="utf-8")
        self.assertEqual(out.returncode, 2)

    def test_tutor_can_report_on_archived_publication(self):
        self.ready()
        self.draft()
        self.publish()
        self.draft("v2")
        self.publish()
        result = rf.record(self.root, {"lesson_id": "L01", "lesson_version": "v1",
            "material_location": "old version", "user_question": "Synthetic old question",
            "response_summary": "Synthetic response", "evidence_kind": "explanation_only"})
        self.assertTrue((self.root / result["path"]).is_file())

    def test_short_lecture_cannot_publish(self):
        self.ready()
        self.draft()
        self.put("lessons/L01/v1/lesson.md", "# Synthetic fixture\n\nA short outline.\n![Diagram](diagram.svg)\n")
        with self.assertRaisesRegex(cs.WorkspaceError, "too short"):
            self.publish()
        self.assertEqual(cs.load_state(self.root)["stage"], "authoring_lesson")

    def test_long_text_cannot_replace_missing_materials(self):
        self.ready()
        self.draft()
        # Delete only this known fixture file, not a user workspace.
        (self.root / "materials/index.md").unlink()
        with self.assertRaisesRegex(cs.WorkspaceError, "materials/index"):
            self.publish()

    def test_source_bibliography_is_not_a_materials_pack(self):
        self.ready()
        catalog = cs.read_json(self.root / "materials/catalog.json")
        catalog["materials"][0].update(availability="unavailable")
        self.put("materials/catalog.json", catalog)
        with self.assertRaisesRegex(cs.WorkspaceError, "Core material unavailable"):
            self.update(stage="ready")

    def test_after_class_reading_is_required(self):
        self.ready()
        catalog = cs.read_json(self.root / "materials/catalog.json")
        catalog["lessons"][0]["after"] = []
        self.put("materials/catalog.json", catalog)
        self.assertFalse(cs.check_materials(self.root, "L01")["ok"])

    def test_missing_or_unembedded_visuals_cannot_publish(self):
        self.ready()
        meta = self.draft()
        self.put("lessons/L01/v1/lesson.md", self.long_body().replace("![Synthetic diagram](diagram.svg)", ""))
        with self.assertRaisesRegex(cs.WorkspaceError, "not embedded"):
            self.publish()
        meta["assets"] = []
        self.put("lessons/L01/lesson.meta.json", meta)
        with self.assertRaisesRegex(cs.WorkspaceError, "No embedded teaching visuals"):
            self.publish()

    def test_reading_callback_must_locate_actual_lesson_text(self):
        self.ready()
        meta = self.draft()
        meta["delivery"]["callbacks"][0]["lesson_location"] = "Nonexistent lesson location"
        self.put("lessons/L01/lesson.meta.json", meta)
        with self.assertRaisesRegex(cs.WorkspaceError, "existing lesson location"):
            self.publish()

    def test_short_format_requires_explicit_record(self):
        self.ready()
        meta = self.draft()
        self.put("lessons/L01/v1/lesson.md", "# Synthetic fixture\n\nA deliberately short protocol fixture.\n![Diagram](diagram.svg)\n")
        meta["delivery"].update(lecture_minutes=5, override={"lecture_minutes": 5, "min_prose_units": 4,
            "reason": "Synthetic user-requested short format fixture", "confirmation_ref": "missing-user-request.md"})
        self.put("lessons/L01/lesson.meta.json", meta)
        with self.assertRaisesRegex(cs.WorkspaceError, "missing-user-request"):
            self.publish()
        self.put("missing-user-request.md", "Synthetic consent fixture; not a real user decision")
        self.publish()
        self.assertEqual(cs.load_state(self.root)["stage"], "awaiting_learner")

    def test_code_tables_quotes_do_not_inflate_main_body_count(self):
        plain = "正文内容。 Some actual prose."
        padding = "\n# 标题\n| 表格 | 数据 |\n> 引用\n```python\n" + "填充" * 14000 + "\n```\n![图](image.svg)\n"
        self.assertEqual(cs.prose_units(plain), cs.prose_units(plain + padding))

    def test_inline_mermaid_requires_matching_source(self):
        self.ready()
        meta = self.draft()
        code = "flowchart LR\n A --> B"
        self.put("lessons/L01/v1/relation.mmd", code)
        meta["assets"] = [{"kind": "diagram", "path": "lessons/L01/v1/relation.mmd", "purpose": "synthetic", "provenance": "synthetic", "checked": True, "embedded_anchor": "relation"}]
        self.put("lessons/L01/lesson.meta.json", meta)
        self.put("lessons/L01/v1/lesson.md", self.long_body() + '\n<a id="relation"></a>\n```mermaid\n' + code + '\n```\n')
        self.assertTrue(cs.check_delivery(self.root, "L01")["ok"])
        self.put("lessons/L01/v1/relation.mmd", "flowchart LR\n A --> C")
        self.assertFalse(cs.check_delivery(self.root, "L01")["ok"])


if __name__ == "__main__":
    unittest.main()
