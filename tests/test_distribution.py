import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from build_release import build
from install_skills import install
from validate_library import validate


class DistributionTests(unittest.TestCase):
    def setUp(self):
        area = (ROOT / "build/test-workspaces").resolve()
        area.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=area)
        assert Path(self.temp.name).resolve().is_relative_to(area)
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()

    def test_install_and_collision_preserve_existing_files(self):
        dest = self.work / "discovery/skills"
        result = install(dest)
        self.assertEqual(len(result["copied"]), 2)
        for name in ("professor", "course-tutor"):
            self.assertEqual((dest / name / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
        marker = dest / "professor/SKILL.md"
        marker.write_text("Existing user change", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            install(dest)
        self.assertEqual(marker.read_text(), "Existing user change")
        # Isolated installation can initialize a course using its own assets.
        script = dest / "professor/scripts/course_state.py"
        spec = importlib.util.spec_from_file_location("staged_course_state", script)
        cs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cs)
        course = self.work / "new-course"
        cs.init_workspace(course, "Synthetic staged install")
        self.assertTrue(cs.check_workspace(course)["ok"])

    def test_release_roundtrip_and_overwrite_refusal(self):
        source = self.work / "source"
        shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns("build", "dist", ".git", "__pycache__", "*.pyc"))
        self.assertTrue(validate(source)["ok"])
        out = self.work / "release"
        result = build(out, source)
        self.assertEqual(len(result["archives"]), 4)
        with self.assertRaises(FileExistsError):
            build(out, source)
        for archive in out.glob("*.zip"):
            with zipfile.ZipFile(archive) as z:
                names = z.namelist()
                self.assertTrue(names)
                self.assertTrue(all(not name.startswith("/") and ".." not in Path(name).parts for name in names))
                self.assertFalse(any("__pycache__" in name or "/build/" in name for name in names))
                target = self.work / archive.stem
                # These archives were just built locally; every entry is containment-checked.
                for name in names:
                    self.assertTrue((target / name).resolve().is_relative_to(target.resolve()))
                z.extractall(target)
                if "-source" in archive.name or "-plugin" in archive.name:
                    self.assertTrue(validate(target / "deep-learning-skills")["ok"])
                    self.assertEqual((target / "deep-learning-skills/LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
                else:
                    skill = "course-tutor" if archive.name.startswith("course-tutor") else "professor"
                    self.assertTrue((target / skill / "SKILL.md").is_file())
                    self.assertEqual((target / skill / "LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())


if __name__ == "__main__":
    unittest.main()
